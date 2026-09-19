// v3_json_architecture/include/common.h

#ifndef EIID_COMMON_H
#define EIID_COMMON_H

#include <cstddef>

// 整个重建核心中所有需要计算精度的实数都写成 Decimal。
// 如果将来要统一改变计算精度，只需要修改下面这一行。
#define Decimal double

constexpr Decimal PI = static_cast<Decimal>(3.141592653589793238462643383279502884L);
constexpr Decimal ELECTRON_MASS_MEV = static_cast<Decimal>(0.511L);

#endif
