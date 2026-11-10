# dc_setup.tcl - EDIT THIS FILE ONCE for your standard-cell library.
#
# The default below assumes the Synopsys SAED32 educational library, which
# most university Synopsys installs include. Point LIB_DIR at your copy
# (or set the SAED32_LIB environment variable) and pick a corner.

if {[info exists env(SAED32_LIB)]} {
    set LIB_DIR $env(SAED32_LIB)
} else {
    set LIB_DIR "/path/to/SAED32_EDK/lib/stdcell_rvt/db_nldm"   ;# <-- edit me
}
set TARGET_DB "saed32rvt_tt1p05v25c.db"

if {![file exists [file join $LIB_DIR $TARGET_DB]]} {
    puts "ERROR: [file join $LIB_DIR $TARGET_DB] not found."
    puts "       Edit synth/dc/dc_setup.tcl or set SAED32_LIB."
    exit 1
}

set_app_var search_path    [concat . $LIB_DIR $search_path]
set_app_var target_library [list $TARGET_DB]
set_app_var link_library   [concat * $TARGET_DB dw_foundation.sldb]
set_app_var synthetic_library [list dw_foundation.sldb]

# Optional realistic boundary conditions (cell names are SAED32; change for
# other libraries, or comment out). Applied by dc_syn.tcl if set.
set DRIVING_CELL "INVX1_RVT"
set OUTPUT_LOAD  0.005
