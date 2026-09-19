#!/usr/bin/env bash

# EIID V7 dependency configurator.
#
# Run this script once on each machine. It discovers the installed ROOT,
# HEALPix, nlohmann/json and (optionally) Geant4 locations, then writes their
# absolute paths to config/local.mk. Normal builds no longer depend on an
# activated Conda/Mamba/Pixi shell or on CONDA_PREFIX.

set -euo pipefail

PROJECT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="${PROJECT_DIRECTORY}/config/local.mk"
TEMPORARY_FILE="${OUTPUT_FILE}.tmp"

fail()
{
    printf 'configure.sh: ERROR: %s\n' "$1" >&2
    exit 1
}

first_executable()
{
    local name="$1"
    local candidate=""
    local known_candidate=""

    # Prefer explicit/project environments over PATH.  Shared servers may put
    # a Snap ROOT in PATH that was built against a newer GLIBC than the host,
    # while the project's ROOT/HEALPix environment is already installed under
    # a known prefix.  Keeping ROOT and HEALPix in the same prefix also avoids
    # mixing two incompatible dependency stacks.
    for known_candidate in \
        "${EIID_DEPS_PREFIX:-}/bin/${name}" \
        "${CONDA_PREFIX:-}/bin/${name}" \
        "${VIRTUAL_ENV:-}/bin/${name}" \
        "${HOME}/micromamba/envs/root-env/bin/${name}" \
        "${HOME}/.conda/envs/root-env/bin/${name}" \
        "${HOME}/miniconda3/envs/root-env/bin/${name}" \
        "${HOME}/miniforge3/envs/root-env/bin/${name}" \
        "${HOME}/anaconda3/envs/root-env/bin/${name}"
    do
        if [[ -x "${known_candidate}" ]]
        then
            printf '%s\n' "${known_candidate}"
            return 0
        fi
    done

    candidate="$(command -v "${name}" 2>/dev/null || true)"

    if [[ -n "${candidate}" && -x "${candidate}" ]]
    then
        printf '%s\n' "${candidate}"
        return 0
    fi

    candidate="$(
        find "${HOME}" \
            -type f \
            -path "*/bin/${name}" \
            ! -path "*-build/*" \
            -perm -u+x \
            -print -quit 2>/dev/null || true
    )"

    if [[ -n "${candidate}" ]]
    then
        printf '%s\n' "${candidate}"
        return 0
    fi

    return 1
}

highest_available_executable()
{
    local name="$1"
    local candidate=""
    local version=""
    local path_candidate=""
    local selected=""

    path_candidate="$(command -v "${name}" 2>/dev/null || true)"

    # Collect every plausible installed copy instead of letting PATH win.
    # This matters on shared servers, where PATH may still expose an old
    # Geant4 even though a newer installation exists below /opt.
    selected="$(
        {
            if [[ -n "${path_candidate}" && -x "${path_candidate}" ]]
            then
                printf '%s\n' "${path_candidate}"
            fi

            for candidate in \
                "${EIID_DEPS_PREFIX:-}/bin/${name}" \
                "${CONDA_PREFIX:-}/bin/${name}" \
                "${VIRTUAL_ENV:-}/bin/${name}" \
                "${HOME}/micromamba/envs/root-env/bin/${name}" \
                "${HOME}/.conda/envs/root-env/bin/${name}" \
                "${HOME}/miniconda3/envs/root-env/bin/${name}" \
                "${HOME}/miniforge3/envs/root-env/bin/${name}" \
                "${HOME}/anaconda3/envs/root-env/bin/${name}"
            do
                if [[ -x "${candidate}" ]]
                then
                    printf '%s\n' "${candidate}"
                fi
            done

            find "${HOME}" /opt /usr/local \
                -type f \
                -path "*/bin/${name}" \
                ! -path "*-build/*" \
                -perm -u+x \
                -print 2>/dev/null || true
        } | awk '!seen[$0]++' | while IFS= read -r candidate
        do
            case "${candidate}" in
                *-build/*)
                    continue
                    ;;
            esac

            version="$("${candidate}" --version 2>/dev/null | head -n 1 || true)"

            if [[ -n "${version}" ]]
            then
                printf '%s\t%s\n' "${version}" "${candidate}"
            fi
        done | sort -V -k1,1 | tail -n 1 | cut -f 2-
    )"

    if [[ -n "${selected}" && -x "${selected}" ]]
    then
        printf '%s\n' "${selected}"
        return 0
    fi

    return 1
}

first_file()
{
    local relative_path="$1"
    shift
    local prefix=""

    for prefix in "$@"
    do
        if [[ -n "${prefix}" && -f "${prefix}/${relative_path}" ]]
        then
            printf '%s\n' "${prefix}/${relative_path}"
            return 0
        fi
    done

    return 1
}

contains_whitespace()
{
    [[ "$1" =~ [[:space:]] ]]
}

ROOT_CONFIG_PATH="${ROOT_CONFIG:-}"
PROJECT_CXX_STANDARD="${PROJECT_CXX_STANDARD:-c++20}"
CXX_PATH="$(command -v "${CXX:-g++}" 2>/dev/null || true)"

if [[ -z "${CXX_PATH}" ]]
then
    fail "C++ compiler was not found: ${CXX:-g++}"
fi

if ! printf 'int main() { return 0; }\n' | \
    "${CXX_PATH}" "-std=${PROJECT_CXX_STANDARD}" -x c++ -fsyntax-only - \
    >/dev/null 2>&1
then
    fail "${CXX_PATH} does not support -std=${PROJECT_CXX_STANDARD}."
fi

if [[ -z "${ROOT_CONFIG_PATH}" ]]
then
    ROOT_CONFIG_PATH="$(first_executable root-config || true)"
elif [[ ! -x "${ROOT_CONFIG_PATH}" ]]
then
    fail "ROOT_CONFIG is not executable: ${ROOT_CONFIG_PATH}"
fi

if [[ -z "${ROOT_CONFIG_PATH}" ]]
then
    fail "root-config was not found under PATH or HOME. Install/locate ROOT first."
fi

ROOT_PREFIX="$(${ROOT_CONFIG_PATH} --prefix 2>/dev/null || true)"
ROOT_LIBRARY_DIRECTORY="$(${ROOT_CONFIG_PATH} --libdir 2>/dev/null || true)"

PREFIX_CANDIDATES=(
    "${EIID_DEPS_PREFIX:-}"
    "${CONDA_PREFIX:-}"
    "${VIRTUAL_ENV:-}"
    "${ROOT_PREFIX}"
    "${HOME}/micromamba/envs/root-env"
    "${HOME}/.conda/envs/root-env"
    "${HOME}/miniconda3/envs/root-env"
    "${HOME}/miniforge3/envs/root-env"
    "${HOME}/anaconda3/envs/root-env"
)

HEALPIX_HEADER="$(first_file include/healpix_cxx/healpix_base.h "${PREFIX_CANDIDATES[@]}" || true)"

if [[ -z "${HEALPIX_HEADER}" ]]
then
    HEALPIX_HEADER="$(find "${HOME}" -type f -path '*/include/healpix_cxx/healpix_base.h' -print -quit 2>/dev/null || true)"
fi

if [[ -z "${HEALPIX_HEADER}" ]]
then
    fail "healpix_base.h was not found. Set EIID_DEPS_PREFIX to the dependency prefix and rerun."
fi

HEALPIX_INCLUDE_DIRECTORY="${HEALPIX_HEADER%/healpix_base.h}"
HEALPIX_PREFIX="${HEALPIX_INCLUDE_DIRECTORY%/include/healpix_cxx}"
HEALPIX_LIBRARY_DIRECTORY=""

for candidate in "${HEALPIX_PREFIX}/lib" "${HEALPIX_PREFIX}/lib64"
do
    if compgen -G "${candidate}/libhealpix_cxx.*" >/dev/null &&
       compgen -G "${candidate}/libcxxsupport.*" >/dev/null
    then
        HEALPIX_LIBRARY_DIRECTORY="${candidate}"
        break
    fi
done

if [[ -z "${HEALPIX_LIBRARY_DIRECTORY}" ]]
then
    fail "libhealpix_cxx and libcxxsupport were not found beside ${HEALPIX_HEADER}."
fi

JSON_HEADER="$(first_file include/nlohmann/json.hpp "${HEALPIX_PREFIX}" "${ROOT_PREFIX}" /usr/local /usr || true)"

if [[ -z "${JSON_HEADER}" ]]
then
    JSON_HEADER="$(find "${HOME}" -type f -path '*/include/nlohmann/json.hpp' -print -quit 2>/dev/null || true)"
fi

if [[ -z "${JSON_HEADER}" ]]
then
    fail "nlohmann/json.hpp was not found. Set EIID_DEPS_PREFIX and rerun."
fi

JSON_INCLUDE_DIRECTORY="${JSON_HEADER%/nlohmann/json.hpp}"
GEANT4_CONFIG_PATH="${GEANT4_CONFIG:-}"

if [[ -z "${GEANT4_CONFIG_PATH}" ]]
then
    # Compare every installed candidate by version. An old geant4-config in
    # PATH must not hide a newer shared installation below /opt.
    GEANT4_CONFIG_PATH="$(highest_available_executable geant4-config || true)"
elif [[ ! -x "${GEANT4_CONFIG_PATH}" ]]
then
    fail "GEANT4_CONFIG is not executable: ${GEANT4_CONFIG_PATH}"
fi
GEANT4_LIBRARY_DIRECTORY=""

if [[ -n "${GEANT4_CONFIG_PATH}" ]]
then
    GEANT4_PREFIX="$(${GEANT4_CONFIG_PATH} --prefix 2>/dev/null || true)"

    for candidate in "${GEANT4_PREFIX}/lib" "${GEANT4_PREFIX}/lib64"
    do
        if compgen -G "${candidate}/libG4*.so*" >/dev/null
        then
            GEANT4_LIBRARY_DIRECTORY="${candidate}"
            break
        fi
    done
fi

for value in \
    "${ROOT_CONFIG_PATH}" \
    "${HEALPIX_INCLUDE_DIRECTORY}" \
    "${HEALPIX_LIBRARY_DIRECTORY}" \
    "${JSON_INCLUDE_DIRECTORY}" \
    "${GEANT4_CONFIG_PATH}"
do
    if [[ -n "${value}" ]] && contains_whitespace "${value}"
    then
        fail "Dependency paths containing whitespace are unsupported: ${value}"
    fi
done

# Emit legacy DT_RPATH instead of DT_RUNPATH.  DT_RPATH is inherited while
# resolving transitive Geant4 dependencies and is not displaced by an old
# Geant4 path already present in LD_LIBRARY_PATH on a shared server.
RPATH_FLAGS="-Wl,--disable-new-dtags -Wl,-rpath,${HEALPIX_LIBRARY_DIRECTORY}"

if [[ -n "${ROOT_LIBRARY_DIRECTORY}" && "${ROOT_LIBRARY_DIRECTORY}" != "${HEALPIX_LIBRARY_DIRECTORY}" ]]
then
    RPATH_FLAGS+=" -Wl,-rpath,${ROOT_LIBRARY_DIRECTORY}"
fi

if [[ -n "${GEANT4_LIBRARY_DIRECTORY}" &&
      "${GEANT4_LIBRARY_DIRECTORY}" != "${HEALPIX_LIBRARY_DIRECTORY}" &&
      "${GEANT4_LIBRARY_DIRECTORY}" != "${ROOT_LIBRARY_DIRECTORY}" ]]
then
    RPATH_FLAGS+=" -Wl,-rpath,${GEANT4_LIBRARY_DIRECTORY}"
fi

mkdir -p "${PROJECT_DIRECTORY}/config"

{
    printf '# Generated by configure.sh. Do not copy this file between machines.\n'
    printf 'EIID_LOCAL_CONFIGURED := 1\n'
    printf 'PROJECT_CXX_STANDARD := %s\n' "${PROJECT_CXX_STANDARD}"
    printf 'CXX := %s\n' "${CXX_PATH}"
    printf 'EIID_DEPS_PREFIX := %s\n' "${HEALPIX_PREFIX}"
    printf 'ROOT_CONFIG := %s\n' "${ROOT_CONFIG_PATH}"
    printf 'HEALPIX_CFLAGS := -I%s\n' "${HEALPIX_INCLUDE_DIRECTORY}"
    printf 'HEALPIX_LIBS := -L%s -lhealpix_cxx -lcxxsupport\n' "${HEALPIX_LIBRARY_DIRECTORY}"
    printf 'JSON_CFLAGS := -I%s\n' "${JSON_INCLUDE_DIRECTORY}"
    printf 'EIID_RPATH_FLAGS := %s\n' "${RPATH_FLAGS}"

    if [[ -n "${GEANT4_CONFIG_PATH}" ]]
    then
        printf 'GEANT4_CONFIG := %s\n' "${GEANT4_CONFIG_PATH}"
        printf 'EIID_HAVE_GEANT4 := 1\n'
    else
        printf 'GEANT4_CONFIG := geant4-config\n'
        printf 'EIID_HAVE_GEANT4 := 0\n'
    fi
} > "${TEMPORARY_FILE}"

mv "${TEMPORARY_FILE}" "${OUTPUT_FILE}"

printf '\nEIID V7 dependency configuration written to:\n  %s\n\n' "${OUTPUT_FILE}"
printf 'C++ compiler:    %s\n' "${CXX_PATH}"
printf 'C++ standard:    %s\n' "${PROJECT_CXX_STANDARD}"
printf 'ROOT config:     %s\n' "${ROOT_CONFIG_PATH}"
printf 'HEALPix header:  %s\n' "${HEALPIX_HEADER}"
printf 'HEALPix library: %s\n' "${HEALPIX_LIBRARY_DIRECTORY}"
printf 'JSON header:     %s\n' "${JSON_HEADER}"

if [[ -n "${GEANT4_CONFIG_PATH}" ]]
then
    printf 'Geant4 config:   %s\n' "${GEANT4_CONFIG_PATH}"
    printf 'Geant4 version:  %s\n' "$("${GEANT4_CONFIG_PATH}" --version 2>/dev/null | head -n 1)"
else
    printf 'Geant4 config:   NOT FOUND (other modules remain buildable)\n'
fi

printf '\nNow run: make all\n'
