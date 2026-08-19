#ifndef EIID_COMMON_H
#define EIID_COMMON_H

#include <cstddef>

// 整个程序中所有需要计算精度的实数都写成 Decimal。
// 调试结束后，只需把下面这一行的 double 改成 long double，就能统一提高计算精度。
#define Decimal double

constexpr Decimal PI = static_cast<Decimal>(3.141592653589793238462643383279502884L);
constexpr Decimal ELECTRON_MASS_MEV = static_cast<Decimal>(0.511L);
constexpr Decimal DENOMINATOR_FLOOR = static_cast<Decimal>(1.0e-12L);

#endif
