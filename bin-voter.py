#!/usr/bin/env python3
import os
import argparse
import sys
import csv
from collections import Counter

def _attempt_vote(byte_list, num_files, threshold, margin, offset, input_files):
    """
    Internal helper to perform a single voting attempt on a list of bytes.
    This is the core voting logic, including absolute and margin thresholds.
    """
    if not byte_list:
        raise ValueError("Cannot vote on an empty list of bytes.")

    # Helper to create a detailed breakdown of which file provided which byte.
    def get_detailed_breakdown():
        breakdown = ["Contributing values:"]
        files_to_report = input_files
        if len(byte_list) != len(input_files):
             return f"Contributing values (after filtering): {[f'0x{b:02X}' for b in byte_list]}"

        for filename, byte_val in zip(files_to_report, byte_list):
            breakdown.append(f"  - {os.path.basename(filename)}: 0x{byte_val:02X}")
        return "\n".join(breakdown)

    counts = Counter(byte_list)
    most_common_list = counts.most_common()

    # Check for a tie
    if len(most_common_list) > 1 and most_common_list[0][1] == most_common_list[1][1]:
        max_count = most_common_list[0][1]
        tied_values = [f"0x{b:02X}" for b, c in most_common_list if c == max_count]
        raise ValueError(
            f"Tie detected for most common byte. "
            f"Values {', '.join(tied_values)} each appeared {max_count} time(s).\n"
            f"{get_detailed_breakdown()}"
        )

    most_common_byte, winner_count = most_common_list[0]
    agreement = winner_count / num_files

    # Check 1: Absolute threshold
    if agreement >= threshold:
        return most_common_byte, counts

    # Check 2: Margin of victory (if absolute threshold fails)
    if margin is not None and len(most_common_list) > 1:
        runner_up_count = most_common_list[1][1]
        if runner_up_count > 0:
            calculated_margin = (winner_count - runner_up_count) / runner_up_count
            if calculated_margin >= margin:
                if 'verbose' in sys.argv or '-v' in sys.argv:
                    print(f"\nNotice at offset 0x{offset:X}: Absolute threshold not met, but margin of victory ({calculated_margin:.2%}) is sufficient. Passing.")
                return most_common_byte, counts

    # If both checks fail, raise a detailed error
    options_str = ", ".join([f"0x{b:02X} ({c} votes)" for b, c in counts.items()])
    error_msg = (
        f"Agreement threshold not met. "
        f"Most common byte 0x{most_common_byte:02X} appeared in {winner_count}/{num_files} files ({agreement:.2%}). "
        f"Required: {threshold:.2%}.\n"
    )
    if margin is not None:
        if len(most_common_list) > 1:
            runner_up_count = most_common_list[1][1]
            calculated_margin = (winner_count - runner_up_count) / runner_up_count
            error_msg += (
                f"Margin of victory over runner-up was {calculated_margin:.2%}. "
                f"Required: {margin:.2%}.\n"
            )
        else:
            error_msg += "No runner-up to calculate margin of victory.\n"
    error_msg += (
        f"All options: [ {options_str} ]\n"
        f"{get_detailed_breakdown()}"
    )
    raise ValueError(error_msg)

def get_voted_byte(byte_list, num_files, threshold, margin, offset, ignore_nulls, interactive, input_files):
    """
    Finds the most common byte, with retry and interactive conflict resolution.
    """
    try:
        return _attempt_vote(byte_list, num_files, threshold, margin, offset, input_files)
    except ValueError as e:
        if ignore_nulls and 0x00 in byte_list:
            print(f"\nNotice at offset 0x{offset:X}: Vote failed. Ignoring 0x00 bytes and re-evaluating as requested.")
            
            filtered_data = [(b, f) for b, f in zip(byte_list, input_files) if b != 0x00]
            if not filtered_data:
                 raise ValueError(f"\n\nError at offset 0x{offset:X}: Vote failed because only 0x00 bytes were present and were ignored.")

            filtered_byte_list, filtered_files_list = zip(*filtered_data)

            try:
                return _attempt_vote(list(filtered_byte_list), num_files, threshold, margin, offset, list(filtered_files_list))
            except ValueError as retry_e:
                e = retry_e # The retry failed, so we'll use its error for the interactive prompt
        
        full_error_message = f"\n\nError at offset 0x{offset:X}: {e}"
        if interactive:
            print(full_error_message, file=sys.stderr)
            print("--- Interactive Conflict Resolution ---", file=sys.stderr)
            
            counts = Counter(byte_list)
            sorted_candidates = counts.most_common()

            print("Please select the byte to write:")
            for i, (byte, count) in enumerate(sorted_candidates):
                print(f"  {i+1}) 0x{byte:02X} ({count} votes)")

            while True:
                try:
                    choice_str = input(f"Enter choice (1-{len(sorted_candidates)}): ")
                    choice_idx = int(choice_str) - 1
                    if 0 <= choice_idx < len(sorted_candidates):
                        chosen_byte = sorted_candidates[choice_idx][0]
                        print(f"User selected 0x{chosen_byte:02X} for offset 0x{offset:X}.")
                        return chosen_byte, counts
                    else:
                        print("Invalid choice. Please try again.", file=sys.stderr)
                except (ValueError, IndexError):
                    print("Invalid input. Please enter a number from the list.", file=sys.stderr)
        else:
            raise ValueError(full_error_message) from e


def create_corrected_firmware(input_files, output_file, threshold, margin, verbose, report_file, chunk_size, force, ignore_nulls, interactive):
    """
    Reads multiple firmware files and creates a new file where each byte
    is the most common byte at that position from the input files.
    """
    if not input_files:
        print("Error: No input files provided.")
        return

    if os.path.exists(output_file) and not force:
        print(f"Error: Output file '{output_file}' already exists. Use --force to overwrite.")
        sys.exit(1)

    try:
        first_file_size = os.path.getsize(input_files[0])
        for f in input_files[1:]:
            if os.path.getsize(f) != first_file_size:
                print(f"Error: File '{f}' has a different size. All files must be the same length.")
                return
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    print(f"Processing {len(input_files)} files, each of size: {first_file_size} bytes.")
    print(f"Agreement threshold set to {threshold:.2%}.")
    if margin is not None: print(f"Margin of victory threshold set to {margin:.2%}.")
    if report_file: print(f"Discrepancy report will be saved to: {report_file}")
    if force and os.path.exists(output_file): print(f"Warning: Overwriting existing output file '{output_file}'.")
    else: print(f"Output will be written to: {output_file}")
    print("Working...")

    discrepancy_count, report_data, file_handles = 0, [], []

    try:
        file_handles = [open(f, 'rb') for f in input_files]
        
        with open(output_file, 'wb') as out_f:
            bytes_processed = 0
            while bytes_processed < first_file_size:
                chunks = [fh.read(chunk_size) for fh in file_handles]
                if not any(chunks): break

                for i in range(len(chunks[0])):
                    current_offset = bytes_processed + i
                    bytes_at_position = [chunk[i] for chunk in chunks]

                    if not all(b == bytes_at_position[0] for b in bytes_at_position):
                        discrepancy_count += 1
                        most_common_int, counts = get_voted_byte(bytes_at_position, len(file_handles), threshold, margin, current_offset, ignore_nulls, interactive, input_files)
                        
                        if verbose and not interactive: # Don't double-print in interactive mode
                            options_str = ", ".join([f"0x{b:02X} ({c} votes)" for b, c in counts.items()])
                            print(f"\nDiscrepancy at offset 0x{current_offset:X}: Winning byte is 0x{most_common_int:02X}. Options: [ {options_str} ]")

                        if report_file:
                            report_data.append({
                                'offset': f'0x{current_offset:X}',
                                'winning_byte': f'0x{most_common_int:02X}',
                                'agreement': f'{counts.get(most_common_int, 0)}/{len(file_handles)}',
                                'all_votes': ", ".join([f"0x{b:02X}({c})" for b, c in Counter(bytes_at_position).items()])
                            })
                    else:
                        most_common_int = bytes_at_position[0]

                    out_f.write(most_common_int.to_bytes(1, 'big'))

                bytes_processed += len(chunks[0])
                percentage = (bytes_processed / first_file_size) * 100
                print(f"Processed {bytes_processed}/{first_file_size} bytes ({percentage:.2f}%)", end='\r')

    except (ValueError, KeyboardInterrupt) as e:
        if isinstance(e, KeyboardInterrupt):
            print("\n\nProcess interrupted by user.", file=sys.stderr)
        else:
            print(e, file=sys.stderr)
        out_f.close()
        os.remove(output_file)
        sys.exit(1)
    finally:
        for fh in file_handles: fh.close()

    if report_file and report_data:
        try:
            with open(report_file, 'w', newline='') as csvfile:
                fieldnames = ['offset', 'winning_byte', 'agreement', 'all_votes']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(report_data)
            print(f"\nDiscrepancy report saved to '{report_file}'.")
        except Exception as e:
            print(f"\nError writing report file: {e}", file=sys.stderr)
            
    print(f"\n\nProcessing complete.")
    print(f"Total bytes with disagreements: {discrepancy_count}")
    print(f"Corrected firmware saved to '{output_file}'")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Corrects firmware dumps by finding the most common byte at each position from multiple source files.",
        epilog="Example: python firmware_voter.py -i --margin 0.5 -o corrected.bin dump*.bin"
    )
    
    parser.add_argument('input_files', nargs='+', help='One or more input .bin firmware files to process.')
    parser.add_argument('-o', '--output', default='firmware_corrected.bin', help='The path for the corrected output .bin file (default: firmware_corrected.bin).')
    parser.add_argument('-t', '--threshold', type=float, default=0.65, help='The minimum percentage of total files that must agree on a byte (default: 0.65).')
    parser.add_argument('--margin', type=float, default=None, help='If the absolute threshold fails, use this margin of victory over the runner-up (e.g., 0.5 for 50%%).')
    parser.add_argument('-i', '--interactive', action='store_true', help='On conflict, prompt for a manual byte selection instead of exiting.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print detailed information for each byte with a discrepancy.')
    parser.add_argument('-f', '--force', action='store_true', help='Force overwrite of the output file if it exists.')
    parser.add_argument('--report', help='Generate a CSV report of all discrepancies.')
    parser.add_argument('--chunk-size', type=int, default=8192, help='The number of bytes to read from files at a time (default: 8192).')
    parser.add_argument('--ignore-nulls', action='store_true', help='If a vote fails, retry after excluding 0x00 bytes from the candidates.')

    args = parser.parse_args()

    if not 0.0 <= args.threshold <= 1.0: parser.error("Threshold must be a value between 0.0 and 1.0.")
    if args.margin is not None and args.margin < 0: parser.error("Margin must be a non-negative value.")
    if args.chunk_size <= 0: parser.error("Chunk size must be a positive integer.")

    create_corrected_firmware(args.input_files, args.output, args.threshold, args.margin, args.verbose, args.report, args.chunk_size, args.force, args.ignore_nulls, args.interactive)
