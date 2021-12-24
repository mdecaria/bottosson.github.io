# Copyright(c) 2021 Björn Ottosson

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this softwareand associated documentation files(the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and /or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions :
# The above copyright noticeand this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Michael De Caria - Update
# OKLAB and OKHSV/OKHSL Python implementation of ok_color.h/colorconversion.js
# includes all functions necessary to go sRGB -> OKHSV or sRGB -> OKHSL
# inverse not yet included

import math

def srgb_transfer_function_inv(a):
    if 0.04045 < a:
        return math.pow((a + .055) / 1.055, 2.4)
    else:
        return a / 12.92

def linear_srgb_to_oklab(r,g,b):
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_ = l ** (1.0 / 3)
    m_ = m ** (1.0 / 3)
    s_ = s ** (1.0 / 3)

    return [
        0.2104542553*l_ + 0.7936177850*m_ - 0.0040720468*s_,
        1.9779984951*l_ - 2.4285922050*m_ + 0.4505937099*s_,
        0.0259040371*l_ + 0.7827717662*m_ - 0.8086757660*s_,
    ]

def oklab_to_linear_srgb(L,a,b):

 
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l = l_*l_*l_
    m = m_*m_*m_
    s = s_*s_*s_

    return [
        (+4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
        (-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
        (-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s),
    ]


def compute_max_saturation(a, b):
    # Max saturation will be when one of r, g or b goes below zero.

    # Select different coefficients depending on which component goes below zero first

    if -1.88170328 * a - 0.80936493 * b > 1:
        # Red component
        k0 = 1.19086277; k1 = 1.76576728; k2 = 0.59662641; k3 = 0.75515197; k4 = 0.56771245;
        wl = 4.0767416621; wm = -3.3077115913; ws = 0.2309699292
    elif 1.81444104 * a - 1.19445276 * b > 1:
        # Green component
        k0 = 0.73956515; k1 = -0.45954404; k2 = 0.08285427; k3 = 0.12541070; k4 = 0.14503204;
        wl = -1.2684380046; wm = 2.6097574011; ws = -0.3413193965
    else:
        # Blue component
        k0 = 1.35733652; k1 = -0.00915799; k2 = -1.15130210; k3 = -0.50559606; k4 = 0.00692167;
        wl = -0.0041960863; wm = -0.7034186147; ws = 1.7076147010

    # Approximate max saturation using a polynomial:
    S = k0 + k1 * a + k2 * b + k3 * a * a + k4 * a * b

    # Do one step Halley's method to get closer
    # this gives an error less than 10e6, except for some blue hues where the dS/dh is close to infinite
    # this should be sufficient for most applications, otherwise do two/three steps 

    k_l = 0.3963377774 * a + 0.2158037573 * b
    k_m = -0.1055613458 * a - 0.0638541728 * b
    k_s = -0.0894841775 * a - 1.2914855480 * b


    l_ = 1 + S * k_l
    m_ = 1 + S * k_m
    s_ = 1 + S * k_s

    l = l_ * l_ * l_
    m = m_ * m_ * m_
    s = s_ * s_ * s_

    l_dS = 3 * k_l * l_ * l_
    m_dS = 3 * k_m * m_ * m_
    s_dS = 3 * k_s * s_ * s_

    l_dS2 = 6 * k_l * k_l * l_
    m_dS2 = 6 * k_m * k_m * m_
    s_dS2 = 6 * k_s * k_s * s_

    f  = wl * l     + wm * m     + ws * s
    f1 = wl * l_dS  + wm * m_dS  + ws * s_dS
    f2 = wl * l_dS2 + wm * m_dS2 + ws * s_dS2

    S = S - f * f1 / (f1*f1 - 0.5 * f * f2)

    return S


def find_cusp(a, b):
    # First, find the maximum saturation (saturation S = C/L)
    S_cusp = compute_max_saturation(a, b)

    # Convert to linear sRGB to find the first point where at least one of r,g or b >= 1:
    rgb_at_max = oklab_to_linear_srgb(1, S_cusp * a, S_cusp * b)
    precub = 1 / max([max([rgb_at_max[0], rgb_at_max[1]]), rgb_at_max[2]])
    L_cusp = precub ** (1.0 / 3)
    C_cusp = L_cusp * S_cusp

    return [ L_cusp , C_cusp ]


def find_gamut_intersection(a, b, L1, C1, L0, cusp=None):
    if not cusp:
        # Find the cusp of the gamut triangle
        cusp = find_cusp(a, b)

    # Find the intersection for upper and lower half seprately
    if ((L1 - L0) * cusp[1] - (cusp[0] - L0) * C1) <= 0:
        # Lower half
        t = cusp[1] * L0 / (C1 * cusp[0] + cusp[1] * (L0 - L1))
    else:
        # Upper half

        # First intersect with triangle
        t = cusp[1] * (L0 - 1) / (C1 * (cusp[0] - 1) + cusp[1] * (L0 - L1))

        # Then one step Halley's method
        dL = L1 - L0
        dC = C1

        k_l = +0.3963377774 * a + 0.2158037573 * b
        k_m = -0.1055613458 * a - 0.0638541728 * b
        k_s = -0.0894841775 * a - 1.2914855480 * b

        l_dt = dL + dC * k_l
        m_dt = dL + dC * k_m
        s_dt = dL + dC * k_s

    
        # If higher accuracy is required, 2 or 3 iterations of the following block can be used:
        L = L0 * (1 - t) + t * L1
        C = t * C1

        l_ = L + C * k_l
        m_ = L + C * k_m
        s_ = L + C * k_s

        l = l_ * l_ * l_
        m = m_ * m_ * m_
        s = s_ * s_ * s_

        ldt = 3 * l_dt * l_ * l_
        mdt = 3 * m_dt * m_ * m_
        sdt = 3 * s_dt * s_ * s_

        ldt2 = 6 * l_dt * l_dt * l_
        mdt2 = 6 * m_dt * m_dt * m_
        sdt2 = 6 * s_dt * s_dt * s_

        r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s - 1
        r1 = 4.0767416621 * ldt - 3.3077115913 * mdt + 0.2309699292 * sdt
        r2 = 4.0767416621 * ldt2 - 3.3077115913 * mdt2 + 0.2309699292 * sdt2

        u_r = r1 / (r1 * r1 - 0.5 * r * r2)
        t_r = -r * u_r

        g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s - 1
        g1 = -1.2684380046 * ldt + 2.6097574011 * mdt - 0.3413193965 * sdt
        g2 = -1.2684380046 * ldt2 + 2.6097574011 * mdt2 - 0.3413193965 * sdt2

        u_g = g1 / (g1 * g1 - 0.5 * g * g2)
        t_g = -g * u_g

        b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s - 1
        b1 = -0.0041960863 * ldt - 0.7034186147 * mdt + 1.7076147010 * sdt
        b2 = -0.0041960863 * ldt2 - 0.7034186147 * mdt2 + 1.7076147010  * sdt2

        u_b = b1 / (b1 * b1 - 0.5 * b * b2)
        t_b = -b * u_b

        t_r = t_r if u_r >= 0 else 10e5
        t_g = t_g if u_g >= 0 else 10e5
        t_b = t_b if u_b >= 0 else 10e5

        t += min([t_r, min([t_g, t_b])])

    return t


def get_ST_max(a_,b_, cusp=None):
    if not cusp:
        cusp = find_cusp(a_, b_)

    L = cusp[0]
    C = cusp[1]
    return [C/L, C/(1-L)]

def toe(x):
    k_1 = 0.206
    k_2 = 0.03
    k_3 = (1+k_1)/(1+k_2)
    
    return 0.5*(k_3*x - k_1 + math.sqrt((k_3*x - k_1)*(k_3*x - k_1) + 4*k_2*k_3*x))

def toe_inv(x):
    k_1 = 0.206
    k_2 = 0.03
    k_3 = (1+k_1)/(1+k_2)
    return (x*x + k_1*x)/(k_3*(x+k_2))



def get_Cs(L, a_, b_):

    cusp = find_cusp(a_, b_)

    C_max = find_gamut_intersection(a_,b_,L,1,L,cusp)
    ST_max = get_ST_max(a_, b_, cusp)

    S_mid = 0.11516993 + 1/(
        + 7.44778970 + 4.15901240*b_
        + a_*(- 2.19557347 + 1.75198401*b_
        + a_*(- 2.13704948 -10.02301043*b_ 
        + a_*(- 4.24894561 + 5.38770819*b_ + 4.69891013*a_
        )))
    )

    T_mid = 0.11239642 + 1/(
        + 1.61320320 - 0.68124379*b_
        + a_*(+ 0.40370612 + 0.90148123*b_
        + a_*(- 0.27087943 + 0.61223990*b_ 
        + a_*(+ 0.00299215 - 0.45399568*b_ - 0.14661872*a_
        )))
    )

    k = C_max/min([(L*ST_max[0]), (1-L)*ST_max[1]])

    C_a = L*S_mid
    C_b = (1-L)*T_mid
    C_mid = 0.9*k*math.sqrt(math.sqrt(1/(1/(C_a*C_a*C_a*C_a) + 1/(C_b*C_b*C_b*C_b))));

    C_a = L*0.4
    C_b = (1-L)*0.8

    C_0 = math.sqrt(1/(1/(C_a*C_a) + 1/(C_b*C_b)))

    return [C_0, C_mid, C_max]

def srgb_to_okhsv(r,g,b):
    lab = linear_srgb_to_oklab(
        srgb_transfer_function_inv(r/255),
        srgb_transfer_function_inv(g/255),
        srgb_transfer_function_inv(b/255)
    )
    C = math.sqrt(lab[1]*lab[1] +lab[2]*lab[2])
    a_ = lab[1]/C
    b_ = lab[2]/C

    L = lab[0]
    h = 0.5 + 0.5*math.atan2(-lab[2], -lab[1])/math.pi
    ST_max = get_ST_max(a_,b_)

    S_max = ST_max[0] 
    S_0 = 0.5
    T = ST_max[1]
    k = 1 - S_0/S_max

    t = T/(C+L*T)
    L_v = t*L
    C_v = t*C

    L_vt = toe_inv(L_v)
    C_vt = C_v * L_vt/L_v

    rgb_scale = oklab_to_linear_srgb(L_vt,a_*C_vt,b_*C_vt)
    precub = 1/(max([rgb_scale[0],rgb_scale[1],rgb_scale[2],0]))
    scale_L = precub ** (1.0 / 3)

    L = L/scale_L
    C = C/scale_L

    C = C * toe(L)/L
    L = toe(L)

    v = L/L_v
    s = (S_0+T)*C_v/((T*S_0) + T*k*C_v)
    return [h,s,v]

def srgb_to_okhsl(r,g,b):
    lab = linear_srgb_to_oklab(
        srgb_transfer_function_inv(r/255),
        srgb_transfer_function_inv(g/255),
        srgb_transfer_function_inv(b/255)
    )

    C = math.sqrt(lab[1]*lab[1] +lab[2]*lab[2])
    a_ = lab[1]/C
    b_ = lab[2]/C

    L = lab[0]
    h = 0.5 + 0.5*math.atan2(-lab[2], -lab[1])/math.pi

    Cs = get_Cs(L, a_, b_)
    C_0 = Cs[0]
    C_mid = Cs[1]
    C_max = Cs[2]
    
    if C < C_mid: 
        k_0 = 0
        k_1 = 0.8*C_0
        k_2 = (1-k_1/C_mid)

        t = (C - k_0)/(k_1 + k_2*(C - k_0))
        s = t*0.8
    else:
        k_0 = C_mid
        k_1 = 0.2*C_mid*C_mid*1.25*1.25/C_0
        k_2 = (1 - (k_1)/(C_max - C_mid))

        t = (C - k_0)/(k_1 + k_2*(C - k_0))
        s = 0.8 + 0.2*t

    l = toe(L)
    return [h,s,l]
