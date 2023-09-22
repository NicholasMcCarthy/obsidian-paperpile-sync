# obsidian-paperpile-sync 

## Disclaimer

Please note that this tool is a standalone Python script and **not** a functional plugin for Obsidian. It is designed to be run independently in your Python environment, and the output files it generates can then be imported into Obsidian.

This script does not interact directly with Obsidian or any of its plugins. While the generated Markdown files are compatible with Obsidian, the actual use of these notes within the Obsidian ecosystem is entirely up to you. 

This script simply provides a way to automate the process of converting PDF documents and accompanying JSON data into a format that's friendly for Obsidian users. To leverage the results, please make sure you manually move or copy the outputted Markdown and image files into your desired Obsidian vault location.

This python script parses a directory of PDF files, matches them with a supplied JSON dictionary, and generates notes in the Obsidian markdown format.

## Fuzzy Matching with Paperpile JSON Data

Paperpile's JSON export includes the key `filename` in the attachments for each PDF entry, however this is not always up-to-date when exporting this file from Paperpile, so users beware. 

This script performs a fuzzy matching process between the PDFs and the accompanying JSON data exported from Paperpile. The matching is not based on exact matches but rather uses a probabilistic, fuzzy logic approach. 

This means the script does its best to match each PDF with corresponding JSON data based on similarity, allowing for some level of discrepancies such as small variations in naming or minor inconsistencies. Despite this, it's recommended to maintain the PDFs and JSON data as consistently formatted as possible for best results.

Currently my Paperpile PDFs export to Google Drive with the structure: `[Journal]/[Firstauthor][Year] - [Title]`, and will first attempt to match the JSON citekey with the `[Firstauthor][Year]` string to produce a set of candidates, and then confirm by matching with title. **This is untested with any other format and will break if the title does not come after a '-'.**  

## Usage

```
python3 main.py --input_dir [path_to_input_directory] --json_path [path_to_json_file] --output_dir [path_to_output_directory] [--image_output [path_to_image_output_directory]]
```

If `--image_output` is not provided, it will default to the same as `output_dir`.

### Arguments:

* `--input_dir`: Path to the directory containing the PDF files.
* `--json_path`: Path to the JSON file for matching with the PDFs.
* `--output_dir`: Path to the directory where the output markdown files will be saved.
* `--image_output` (optional): Path to the directory where the output image files will be saved. Defaults to `output_dir` if not specified.

### Configurations:

The script comes with the following configurations, set in the `settings.ini` file.

* `IMAGE_FILETYPE = 'png'`: The file type of the images generated from the PDFs.
* `COLOCATE_IMAGES = False`: Whether to co-locate images with the markdown files.
* `KEYWORDS_AS_TAGS = True`: Whether to use keywords from the JSON as tags.
* `KEYWORDS_TAG_DELIMITER = '_'`: Delimiter used if `KEYWORDS_AS_TAGS = True`.
* `PRINT_ERRORS_TO_CONSOLE = False`: Whether to print errors to console. If `False`, errors will be logged in `sync_errors.md`.
* `ERROR_FILE = 'sync_errors.md'`: File name of the markdown error log.
* `VERBOSE = False`: Whether to display verbose output.

## Note

Please ensure that your Python environment has necessary dependencies installed.

## License

This project is licensed under the terms of the MIT license.