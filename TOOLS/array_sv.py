import argparse

def pow2(p):
    """Calculates 2 to the power of p."""
    return 2**p

def round_near(num):
    """Rounds a number to the nearest integer."""
    # This function was present in the Perl, but not used in the provided snippet.
    return round(num)

def generate_csam_verilog(x_bits, y_bits, module_name=None):
    """
    Generates Verilog code for a Truncated Array Multiplier (CSAM).

    Args:
        x_bits (int): The number of bits for input X.
        y_bits (int): The number of bits for input Y.
        module_name (str, optional): The name of the Verilog module.
                                     Defaults to CSAM_X_Y_Z.
    """

    if x_bits <= 0 or y_bits <= 0:
        print("Input parameters:")
        print("    -x <bits> the number of x bits")
        print("    -y <bits> the number of y bits")
        print("    -m <string> module name (optional)")
        exit(1)

    z_bits = x_bits + y_bits

    pp_label = 1
    ha_label = 1
    fa_label = 1
    cpa_label = 1
    instcnt = 1 # Not used in the Perl script, but initialized.

    # --- Conversion into binary format ---
    # NOTE: $err_tot_rnd and $K were not defined in the original Perl script.
    # Assuming $err_tot_rnd = 0 and $K = 0 for this conversion.
    err_tot_rnd = 0
    K = 0
    carray = [0] * (z_bits + K) # Initialize carray with zeros
    rem = err_tot_rnd
    for j in range(1, z_bits + K + 1):
        mod = rem * pow2(j)
        if mod >= 1:
            rem = rem - 1 / pow2(j)
            carray[x_bits + y_bits - j] = 1
        else:
            carray[x_bits + y_bits - j] = 0

    # --- Calculation of the number of bits required for the constant correction ---
    nbitscon = 0
    # Ensure loop range is valid for carray
    start_idx = x_bits + y_bits - z_bits
    end_idx = x_bits + y_bits
    for j in range(start_idx, end_idx):
        if j < len(carray): # Check bounds
            nbitscon += carray[j] * pow2(j - (x_bits + y_bits - z_bits))

    # --- Calculation of which partial products have to be generated ---
    if x_bits < z_bits:
        x_pp_size = x_bits
        h_pp_size = z_bits - x_bits
    else:
        x_pp_size = z_bits
        h_pp_size = 0

    if y_bits <= z_bits:
        y_pp_size = y_bits
    else:
        y_pp_size = z_bits - 1

    # --- Calculation of the number of bits available for correction ---
    # (number of HA located on the diagonal and on the second line)
    nha = 0
    nhadiag = 0
    for y in range(y_bits - y_pp_size, y_bits):
        for x in range(x_bits - 2, x_bits - x_pp_size -1, -1): # Decrementing loop
            if x + y >= x_bits + y_bits - z_bits:
                if y == y_bits - y_pp_size + 1:
                    nha += 1
            if x + y == x_bits + y_bits - z_bits and y > y_bits - y_pp_size + 1:
                nhadiag += 1

    # --- Write the header of the verilog file (variables definition) ---
    if not module_name:
        print(f"module CSAM_{x_bits}_{y_bits}_{z_bits} (Z, X, Y);")
    else:
        print(f"module {module_name} (Z, X, Y);")
    print("\t")
    print(f"\tinput logic [{y_bits-1}:0] Y;")
    print(f"\tinput logic [{x_bits-1}:0] X;")
    print(f"\toutput logic [{z_bits-1}:0] Z;")
    print("\n\n")

    for y in range(y_bits):
        print(f"\tlogic [{x_bits-1}:0] P{y};")
        print(f"\tlogic [{x_bits-1}:0] carry{y+1};")
        print(f"\tlogic [{x_bits-1}:0] sum{y+1};")
    print(f"\tlogic [{z_bits-2}:0] carry{y_bits+1};")

    print("\n\n")

    # --- Generate the partial products ---
    print("\t// generate the partial products.")
    for y in range(y_bits - y_pp_size, y_bits):
        for x in range(x_bits - 1, x_bits - x_pp_size - 1, -1): # Decrementing loop
            if x + y >= x_bits + y_bits - z_bits:
                if y > y_bits - y_pp_size and x == x_bits - 1:
                    print(f"\tand pp{pp_label}(sum{y}[{x}], X[{x}], Y[{y}]);")
                    pp_label += 1
                else:
                    print(f"\tand pp{pp_label}(P{y}[{x}], X[{x}], Y[{y}]);")
                    pp_label += 1
    print("\n")

    # --- Array Reduction ---
    print("\t// Array Reduction")
    for y in range(y_bits - y_pp_size, y_bits):
        for x in range(x_bits - 2, x_bits - x_pp_size - 1, -1): # Decrementing loop
            if x + y >= x_bits + y_bits - z_bits:
                if y == y_bits - y_pp_size + 1:
                    print(f"\thalf_adder  HA{ha_label}(carry{y}[{x}],sum{y}[{x}],P{y}[{x}],P{y-1}[{x+1}]);")
                    ha_label += 1
                if y > y_bits - y_pp_size + 1:
                    if x + y == x_bits + y_bits - z_bits:
                        print(f"\thalf_adder  HA{ha_label}(carry{y}[{x}],sum{y}[{x}],P{y}[{x}],sum{y-1}[{x+1}]);")
                        ha_label += 1
                    else:
                        print(f"\tfull_adder  FA{fa_label}(carry{y}[{x}],sum{y}[{x}],P{y}[{x}],sum{y-1}[{x+1}],carry{y-1}[{x}]);")
                        fa_label += 1
    print("\n")

    # --- Generate lower order product ---
    print("\t// Generate lower product bits YBITS ")
    z_pin = 0
    if z_bits > x_bits:
        for y in range(y_bits - z_bits + x_bits, y_bits):
            if y == 0:
                print("\tbuf b1(Z[0], P0[0]);")
                z_pin += 1
            else:
                print(f"\tassign Z[{z_pin}] = sum{y}[0];")
                z_pin += 1
    print("\n")

    # --- Generate higher order product ---
    print("\t// Final Carry Propagate Addition")
    nhop = x_bits
    x_start = 0
    for x in range(x_start, x_bits):
        if x == x_start:
            if x == x_bits - nhop:
                print(f"\thalf_adder CPA{cpa_label}(carry{y_bits}[{x}],Z[{z_pin}],carry{y_bits-1}[{x}],sum{y_bits-1}[{x+1}]);")
                cpa_label += 1
                z_pin += 1
            else:
                print(f"\tassign carry{y_bits}[{x}] = carry{y_bits-1}[{x}] & sum{y_bits-1}[{x+1}];")
        else:
            if x == x_bits - 2:
                print(f"\tfull_adder CPA{cpa_label}(Z[{z_pin+1}],Z[{z_pin}],carry{y_bits-1}[{x}],carry{y_bits}[{x-1}],sum{y_bits-1}[{x+1}]);")
                cpa_label += 1
                z_pin += 1
            else:
                if x >= x_bits - nhop and x < x_bits - 2:
                    print(f"\tfull_adder CPA{cpa_label}(carry{y_bits}[{x}],Z[{z_pin}],carry{y_bits-1}[{x}],carry{y_bits}[{x-1}],sum{y_bits-1}[{x+1}]);")
                    cpa_label += 1
                    z_pin += 1
                if x < x_bits - nhop and x > x_start and x < x_bits - 2:
                    print(f"\treduced_full_adder CPA{cpa_label}(carry{y_bits}[{x}],carry{y_bits-1}[{x}],carry{y_bits}[{x-1}],sum{y_bits-1}[{x+1}]);")
                    cpa_label += 1

    print("\nendmodule")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate truncated array multiplier (CSAM) Verilog.")
    parser.add_argument('-x', type=int, required=True, help='The number of x bits')
    parser.add_argument('-y', type=int, required=True, help='The number of y bits')
    parser.add_argument('-m', type=str, help='Module name (optional)')

    args = parser.parse_args()

    generate_csam_verilog(args.x, args.y, args.m)

    
