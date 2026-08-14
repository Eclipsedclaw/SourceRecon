"""可由服务器脚本和测试共同调用的实验重建入口。"""

from __future__ import annotations

from pathlib import Path

from eiid.configuration import load_config
from eiid.convergence import IterationRecorder

from .end_to_end import ExperimentReconstructionApplication
from .run_context import RunContext


def run_experiment(
    config_path: str,
    run_id=None,
    log_path=None,
    run_kind: str = "experiment_reconstruction",
    resume_from_run_id=None,
):
    config = load_config(config_path)
    initial_image = None
    resume_iteration = None
    resume_checkpoint = None
    if resume_from_run_id is not None:
        parent_id = str(resume_from_run_id)
        if Path(parent_id).name != parent_id:
            raise ValueError("resume_from_run_id 不能包含目录。")
        parent_directory = (config.paths.output_root / parent_id).resolve()
        try:
            parent_directory.relative_to(config.paths.output_root)
        except ValueError as error:
            raise ValueError("恢复来源超出 runs 根目录。") from error
        if (parent_directory / "SUCCESS.json").is_file():
            raise ValueError("指定 run 已成功完成，无需恢复：" + parent_id)
        resume_iteration, initial_image, resume_checkpoint = (
            IterationRecorder.load_latest_checkpoint(
                parent_directory / "checkpoints"
            )
        )
    context = RunContext.start(
        config,
        run_kind=run_kind,
        run_id=run_id,
        log_path=log_path,
    )
    try:
        if resume_from_run_id is not None:
            context.add_provenance(
                {
                    "resume_from_run_id": str(resume_from_run_id),
                    "resume_checkpoint": str(resume_checkpoint),
                    "resume_checkpoint_iteration": resume_iteration,
                }
            )
        summary = ExperimentReconstructionApplication(
            config,
            context,
            initial_image=initial_image,
            resumed_from_run_id=resume_from_run_id,
        ).run()
        context.mark_success(summary, stop_reason=summary["stop_reason"])
        return summary
    except BaseException as error:
        if context.status == "running":
            reason = (
                "user_interrupt"
                if isinstance(error, KeyboardInterrupt)
                else "exception"
            )
            context.mark_failure(error, stop_reason=reason)
        raise
