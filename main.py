import os
import glob
import json
import fitz
from fuzzywuzzy import fuzz
from datetime import datetime
from PIL import Image
import re
import argparse
import configparser

config = configparser.ConfigParser()
config.read('settings.ini')

IMAGE_FILETYPE = config.get('SETTINGS', 'IMAGE_FILETYPE')
COLOCATE_IMAGES = config.getboolean('SETTINGS', 'COLOCATE_IMAGES')
KEYWORDS_AS_TAGS = config.getboolean('SETTINGS', 'KEYWORDS_AS_TAGS')
KEYWORDS_TAG_DELIMITER = config.get('SETTINGS', 'KEYWORDS_TAG_DELIMITER')
PRINT_ERRORS_TO_CONSOLE = config.getboolean('SETTINGS', 'PRINT_ERRORS_TO_CONSOLE')
ERROR_FILE = config.get('SETTINGS', 'ERROR_FILE')
VERBOSE = config.getboolean('SETTINGS', 'VERBOSE')

def main(input_dir, json_path, output_dir, image_output_dir):

    pdfs = find_pdfs(input_dir)
    print(f'{len(pdfs)} pdfs found in {input_dir}')

    json_data = load_json(json_path)
    print(f'{len(json_data)} entries found in {json_path}')

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(image_output_dir, exist_ok=True)

    errors = []
    for pdf in pdfs:

        doc_data = fuzzy_match_filename_and_json(pdf, json_data)

        if doc_data:
            if VERBOSE:
                print(f'Extracting {os.path.basename(pdf)} ')
            extract_annotation(pdf, doc_data, output_dir, image_output_dir)
        else:
            errors.append(os.path.basename(pdf))
            if PRINT_ERRORS_TO_CONSOLE:
                print(f'Sync error: {os.path.basename(pdf)}')

    print(f'{len(errors)} pdfs unable to match')

    if ERROR_FILE:
        error_output = os.path.join(output_dir, ERROR_FILE)
        with open(error_output, 'w', encoding='utf8') as f:
            for line in errors:
                f.write(line+'\n')

    print('Extraction complete')


def find_pdfs(input_directory):
    return glob.glob(f'{input_directory}/**/*.pdf', recursive=True)


def load_json(filepath):

    with open(filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)

    citekey_map = {}

    for x in data:

        citekey_map[x['citekey']] = x

       # # filename doesn't appear to get updated to the google drive output any more ?
       #  for a in x.get('attachments', []):
       #      if a['mimeType'] == 'application/pdf':
       #          filename_map[a['filename']] = x
       #          break

    return citekey_map

def sanitize_string(input_string):
    sanitized = re.sub(r'[^\w\s]', '', input_string)
    return sanitized.strip().lower()

def fuzzy_match_filename_and_json(pdf, citekey_map, match_threshold = 0.9):

    # TODO: A better way of doing this !
    # Get pseudo-citekey and title from filename
    bname = os.path.splitext(os.path.basename(pdf))[0]
    doc_citekey = bname.split('-')[0].strip()
    doc_title = ''.join(bname.split('-')[1:]).strip()

    try:
        if doc_citekey != '':

            # Find a set of candidate keys
            candidates = [k for k in citekey_map.keys() if doc_citekey in k]
            match_threshold = 0.9

            # Check if 'doc_title' has a fuzzy match with a value of a candidate key
            for candidate in candidates:
                if fuzz.ratio(citekey_map[candidate]['title'], doc_title)/100 >= match_threshold:
                    return citekey_map[candidate]
        else:
            for x in citekey_map.values():
                if fuzz.ratio(x['title'], doc_title)/100 >= match_threshold:
                    return x

    except KeyError:
        return None

    return None

def get_current_datetime():
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M")

def generate_frontmatter(pdf_data):

    yaml_lines = []

    yaml_lines.append('---')
    yaml_lines.append(f"created: {get_current_datetime()}")

    if value := pdf_data.get('title'):
        value = value.encode('utf-8', 'ignore').decode('utf-8')
        yaml_lines.append(f'title: "{value}"')

    if value := pdf_data.get('author'):
        author_str = ', '.join([x['formatted'] for x in value])
        author_str = author_str.encode('utf-8', 'ignore').decode('utf-8')
        yaml_lines.append(f"author: {author_str}")

    if value := pdf_data.get('journalfull'):
        value = value.encode('utf-8', 'ignore').decode('utf-8')
        yaml_lines.append(f"journal: {value}")

    if value := pdf_data.get('kind'):
        yaml_lines.append(f"kind: {value}")

    if value := pdf_data.get('url'):
        url_str = ', '.join(value)
        yaml_lines.append(f"url: {url_str}")

    if value := pdf_data.get('doi'):
        yaml_lines.append(f"doi: {value}")

    if value := pdf_data.get('publisher'):
        yaml_lines.append(f"publisher: {value}")

    if value := pdf_data.get('published'):
        if year := value.get('year'):
            yaml_lines.append(f"year: {year}")

        if month := value.get('month'):
            yaml_lines.append(f"month: {month}")

    if value := pdf_data.get('citekey'):
        yaml_lines.append(f"citekey: {value}")

    if value := pdf_data.get('keywords'):

        if KEYWORDS_AS_TAGS:
            tags = value.split(';')
            tags = [x.lstrip().rstrip().lower().replace(' ', KEYWORDS_TAG_DELIMITER) for x in tags ]
            tags = [f"#{x}" for x in tags]
            keywords_str = f"{[x for x in tags]}"
            yaml_lines.append(f"tags: {keywords_str}")
        else:
            keywords_str = ', '.join(value.split(';'))
            yaml_lines.append(f"keywords: {keywords_str}")

    if value := pdf_data.get('citekey'):
        yaml_lines.append(f'aliases: ["{value}"]')

    if value := pdf_data.get('filename'):
        yaml_lines.append(f'filename: "{value}"')

    if value := pdf_data.get('labelsNamed'):
        label_str = ', '.join(value)
        yaml_lines.append(f"labels: {label_str}")

    yaml_lines.append('---\n\n')

    out = '\n'.join([line for line in yaml_lines])

    return out.encode('utf-8', 'ignore').decode('utf-8')

def create_markdown_callout(type, header, body, mode):
    out = f"> [!{type}]{mode} {header}\n> {body}\n\n"
    return out

def write_annotations_to_file(frontmatter, annotations, filepath):

    with open(os.path.normpath(filepath), 'w', encoding='utf8') as file:

        file.write(frontmatter)

        for annotation in annotations:

            header = f"Page: {annotation['page_num']}, By: {annotation['title']}, Type: {annotation['subject']} "

            if annotation['type'] in ['Text', 'FreeText']:
                callout = create_markdown_callout('note', header, annotation['content'], '+')
            elif annotation['type'] in ['Highlight', 'Underline']:
                callout = create_markdown_callout('info', header, annotation['content'], '+')
            elif annotation['type'] in ['StrikeOut']:
                callout = create_markdown_callout('warning', header, f"~~{annotation['content'].lstrip().rstrip()}~~", '+')

            elif annotation['type'] in ['Square', 'Freehand', 'Circle', 'Arrow', 'Line', 'Ink']:

                img_path = annotation['content']
                os.makedirs(os.path.dirname(img_path), exist_ok=True)

                # Write image to image output location
                annotation['image'].save(img_path)

                # Get relative path for markdown
                rel_path = os.path.relpath(img_path, os.path.dirname(filepath))
                rel_path = os.path.normpath(rel_path).replace('\\', '/')
                content = f"![[{rel_path}]]"
                callout = create_markdown_callout('tip', header, content, '+')

            file.write(callout)

def extract_annotation(pdf_path, pdf_data, output_dir, image_output_dir):

    doc = fitz.open(pdf_path)

    basename = os.path.splitext(os.path.basename(pdf_path))[0]

    output_fpath = os.path.join(output_dir, f'{basename}.md')
    pdf_data['filename'] = os.path.basename(pdf_path)

    if doc.has_annots():
        # Create frontmatter
        frontmatter = generate_frontmatter(pdf_data)

        # Initialize an empty list for annotations and images
        annotations = []

        # Extract text and images from pdf
        for page in doc:
            for annot in page.annots():

                info = annot.info
                info['page_num'] = page.number
                info['type'] = annot.type[1]

                if info['type'] in ['Text', 'FreeText']:
                    pass
                elif info['type'] in ['Highlight', 'Underline', 'StrikeOut']:
                    content = page.get_textbox(annot.rect)
                    info['content'] = clean_string(content)

                elif info['type'] in ['Square', 'Freehand', 'Circle', 'Arrow', 'Line', 'Ink']:

                    pix = page.get_pixmap(clip=annot.rect, dpi=400)
                    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)

                    img_fname = f"{basename}_page{page.number}_{'-'.join([str(int(x)) for x in annot.rect])}.{IMAGE_FILETYPE}"
                    img_fpath = os.path.join(image_output_dir, img_fname)
                    info['content'] = img_fpath

                    info['image'] = img
                else:
                    print(f"Unknown type: {info['type']}")
                    continue

                annotations.append(info)

        # Write annotations to file
        write_annotations_to_file(frontmatter, annotations, output_fpath)


def clean_string(s):
    """Clean up the string by removing newlines, double spaces, and special character '- '"""

    # Remove newlines
    s = re.sub(r'\n', ' ', s)

    # Replace double whitespace with a single whitespace
    s = re.sub(r'  ', ' ', s)

    # Replace any instances of '- ' with a character immediately in front and after with a ''
    s = re.sub(r'.- .', '', s)

    return s


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Process some directories.")
    parser.add_argument('--input_dir', required=True, help='Input directory')
    parser.add_argument('--json_path', required=True, help='Path to JSON file')
    parser.add_argument('--output_dir', required=True, help='Output directory')
    parser.add_argument('--image_output', required=False, help='Image output directory')

    args = parser.parse_args()

    # If image_output is not set, it will be the same as output_dir
    if not args.image_output:
        args.image_output = args.output_dir

    main(args.input_dir, args.json_path, args.output_dir, args.image_output)
