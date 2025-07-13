# bin-voter - Firmware Dump Majority Voter

**bin-voter** is a command-line utility designed to reconstruct a correct binary file from multiple, slightly corrupted firmware dumps. When taking multiple dumps of a microcontroller's memory, it's common for individual bits to flip, resulting in files that are not byte-for-byte identical.

This tool solves that problem by "voting" on every single byte. It compares all input files and, for each position, writes the most common byte to a new, corrected output file. It is packed with features to handle complex conflict resolution, making it a powerful tool for data recovery and firmware analysis.

## Features

* **Majority & Plurality Voting:** Creates a corrected binary by taking the most common byte at each position from all input files.
* **Flexible Thresholds:**
    * **Absolute Threshold (`-t`):** Ensures the winning byte has a minimum percentage of the total votes (default: 65%).
    * **Margin of Victory (`--margin`):** As an alternative, ensures the winning byte beats the runner-up by a specific margin (e.g., has 50% more votes).
* **Interactive Conflict Resolution (`-i`):** If a vote fails due to a tie or a failed threshold, you can manually choose the correct byte from a sorted list of candidates.
* **Smart Error Handling:**
    * **Tie Detection:** Explicitly detects and reports ties for the most common byte.
    * **Null Byte Exclusion (`--ignore-nulls`):** Optionally retries a failed vote after excluding `0x00` bytes, which can be common artifacts of read errors.
* **Detailed Reporting:**
    * **Verbose Mode (`-v`):** Prints detailed information about every byte that has a discrepancy.
    * **CSV Report (`--report`):** Generates a comprehensive CSV file logging every offset with a disagreement, the winning byte, and the vote counts.
* **Safe & Efficient:**
    * **File Overwrite Protection:** By default, prevents overwriting existing files. Use `--force` to override.
    * **Chunk-Based Processing (`--chunk-size`):** Efficiently processes large files by reading them in chunks.
* **User-Friendly:**
    * All memory offsets are displayed in standard hexadecimal format.
    * Clear progress bar shows processing status.
    * Full command-line argument support with help text.

## Installation

No special installation is required. Just download the script (`bin-voter.py`) and make it executable:

```bash
chmod +x bin-voter.py
```

## Usage

The script is run from the command line, providing a list of input files and optional arguments to control its behavior.

```bash
./bin-voter.py [OPTIONS] <input_file_1> <input_file_2> ...
```

### Arguments

| Argument          | Short       | Description                                                                              | Default                  |
| ----------------- | ----------- | ---------------------------------------------------------------------------------------- | ------------------------ |
| `input_files`     | (Positional)| One or more input `.bin` firmware files to process.                                      | (Required)               |
| `--output <file>` | `-o <file>` | Path for the corrected output file.                                                      | `firmware_corrected.bin` |
| `--threshold <val>`| `-t <val>`  | Minimum percentage (0.0 to 1.0) of files that must agree.                                | `0.65`                   |
| `--margin <val>`  |             | If threshold fails, use this margin of victory over the runner-up (e.g., 0.5 for 50%).   | `None`                   |
| `--interactive`   | `-i`        | On conflict, prompt for a manual byte selection instead of exiting.                      | `False`                  |
| `--verbose`       | `-v`        | Print detailed information for each byte with a discrepancy.                             | `False`                  |
| `--force`         | `-f`        | Force overwrite of the output file if it exists.                                         | `False`                  |
| `--report <file>` |             | Generate a CSV report of all discrepancies.                                              | `None`                   |
| `--ignore-nulls`  |             | If a vote fails, retry after excluding `0x00` bytes.                                     | `False`                  |
| `--chunk-size <N>`|             | Number of bytes to read from files at a time.                                            | `8192`                   |

## Examples

### Basic Usage

Create a corrected file from three dumps, using all default settings.

```bash
./bin-voter.py dump1.bin dump2.bin dump3.bin
```

*Output will be `firmware_corrected.bin`.*

### Setting a Higher Threshold and Reporting

Require 90% agreement and generate a CSV report of all fixed bytes.

```bash
./bin-voter.py -t 0.9 --report discrepancies.csv -o firmware_final.bin dump*.bin
```

### Using Margin of Victory

If the 65% threshold fails, allow a byte to win if it has at least 50% more votes than the runner-up.

```bash
./bin-voter.py --margin 0.5 -o corrected.bin dump*.bin
```

### Interactive Mode

For a difficult set of dumps, manually resolve any conflicts that the automatic rules can't.

```bash
./bin-voter.py -i --ignore-nulls -o my_firmware.bin dump*.bin
```

*If a conflict occurs, the script will pause and prompt you for a decision.*
