#ifndef EIID_V7_COMMON_H
#define EIID_V7_COMMON_H

// V7 的数值精度只有这一处定义。需要整体切换精度时只修改本行。
#define Decimal double

constexpr Decimal PI = static_cast<Decimal>(3.141592653589793238462643383279502884L);
constexpr Decimal ELECTRON_MASS_MEV = static_cast<Decimal>(0.511L);

#endif
