#!/usr/bin/env python
"""
Takes two separate alignments and finds where they agree. Alignment files have one sentence on one line, the aligned
sentence from target language on the next line and then each alignment (pair) is separated by a newline.
Assuming the -a parameter for annotation, it allows the user to decide which annotation is correct where the two did not
agree.
"""
import argparse
import os.path
import subprocess
import curses
from math import ceil

from src.alignments import Alignments
from src.annotation import Annotation
from src.film import Film

MIN_HIGHLIGHT_LENGTH = 4

class CommandCodes:
    DELETE = ord('d')
    EDIT = ord('e')
    SAVE = ord('w')
    SPLIT = ord('s')
    NEXT = ord('j')
    PREV = ord('k')
    JOIN = ord('u')


def main(opts, alignments):
    def draw_ui(stdscr, label1, label2):

        def _show_side(language, window, longest):
            start_of_subs = ceil(longest / content_width) + 1
            if language.has_subtitles():
                available_lines = full_height - start_of_subs - 2
                lines = language.lines().split('\n')
                if len(lines) > available_lines:
                    lines = lines[:available_lines]
                lines = '\n'.join(lines)
                window.addstr(start_of_subs, 0, lines)
                if language.has_utterance():
                    previous_y = start_of_subs
                    for subtitle in language.subtitles:
                        window.addstr(0, 0, language.utterance)
                        y_offset = start_of_subs - 1
                        running_length = 0
                        groups = []
                        for line in lines.split('\n'):
                            y, x_offset, length = language.get_offsets_and_length(line)
                            y_offset += y
                            if length > MIN_HIGHLIGHT_LENGTH:
                                groups.append({'y': y_offset, 'x': x_offset, 'length': length})
                            running_length += length
                            if running_length >= len(language.utterance):
                                break
                        selected = None
                        for group in groups:
                            if group['length'] == len(language.utterance):
                                selected = group
                        if selected is not None:
                            window.chgat(selected['y'], selected['x'], selected['length'], curses.A_STANDOUT)
                        else:
                            for group in groups:
                                window.chgat(group['y'], group['x'], group['length'], curses.A_STANDOUT)

        def show_annotation(annotation: Annotation, extra=None):
            left_window.erase()
            right_window.erase()

            longest = annotation.content_length()

            _show_side(annotation.source, left_window, longest)
            _show_side(annotation.target, right_window, longest)

            left_window.addstr(full_height-1, 0, f'{film.annotation_index}/{film.total} '
                                                 f'TOTAL. [-{film.stranded_count} +{film.added}]')

            left_window.refresh()
            right_window.refresh()

        def edit_annotation(annotation: Annotation):
            curses.endwin()
            with open("/tmp/alignment.txt", 'w', encoding='utf-8') as f:
                if not annotation.has_empty_source():
                    f.write(annotation.source.utterance + '\n')
                if not annotation.has_empty_target():
                    f.write(annotation.target.utterance)
            subprocess.run(['vim', '/tmp/alignment.txt'])
            with open("/tmp/alignment.txt", 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > 1:
                annotation.source.utterance = lines[0].strip()
                annotation.target.utterance = lines[1].strip()
            curses.reset_prog_mode()
            show_annotation(annotation)

        def delete_annotation(annotation: Annotation):
            film.clear_annotation(annotation)
            show_annotation(annotation)

        def split_annotation(annotation: Annotation):
            film.split_annotation()
            curses.flash()
            show_annotation(annotation, 'Annotation duplicated.')

        def join_annotation(annotation: Annotation):
            film.join_annotation_with_subsequent()
            show_annotation(annotation)

        def save_annotations():
            # _, alignments_file = alignment_files(opts.source, opts.target)
            with open(alignments_file.replace('-vec', '-gold'), 'w', encoding='utf-8') as f:
                for annotation in film.annotations:
                    if annotation.has_empty_target() and annotation.has_empty_source():
                        continue
                    if annotation.has_empty_source():
                        f.write('*' * len(annotation.target.utterance) + '\n')
                    else:
                        f.write(annotation.source.utterance + '\n')
                    if annotation.has_empty_target():
                        f.write('*' * len(annotation.source.utterance) + '\n')
                    else:
                        f.write(annotation.target.utterance + '\n')
                    f.write('\n')
            curses.endwin()
            print(f'Saved annotations to: {alignments_file}')
            exit(0)

        k = 0
        # Clear and refresh the screen for a blank canvas
        stdscr.clear()
        stdscr.refresh()
        curses.curs_set(0)
        # Initialization
        full_height, full_width = stdscr.getmaxyx()

        half_width = int(full_width / 2.0)  # middle point of the window
        content_width = half_width - 2

        left_window = curses.newwin(full_height, content_width, 0, 0)
        right_window = curses.newwin(full_height, content_width, 0, half_width+2)
        while k != ord('q'):
            annotation = film.get_annotation()
            show_annotation(annotation)

            k = stdscr.getch()
            match k:
                case curses.KEY_DOWN | CommandCodes.NEXT:
                    film.next()
                case curses.KEY_UP | CommandCodes.PREV:
                    film.previous()
                case CommandCodes.EDIT:
                    edit_annotation(annotation)
                case CommandCodes.DELETE:
                    delete_annotation(annotation)
                case CommandCodes.SPLIT:
                    split_annotation(annotation)
                case CommandCodes.SAVE:
                    save_annotations()
                case CommandCodes.JOIN:
                    join_annotation(annotation)
                case _:
                    pass

    film = Film(opts.source, opts.target, alignments, opts.ignore_empty)
    curses.wrapper(draw_ui, film.source.label, film.target.label)


def run_vecalign(opts):
    subprocess.run(['./scripts/run_vecalign.sh', opts.source, opts.target])


def sent_files_for_srt(srt_file) -> (str, str):
    return srt_file.replace('.srt', '.sent'), srt_file.replace('.srt', '.sent-index')


def alignment_files(source, target) -> (str, str):
    """
    returns a path to the alignments
    and a path to the index file
    """
    source_lang = source.split('/')[-2]
    target_lang = target.split('/')[-2]
    base_dir = source.split("/" + source_lang)[0]
    return f'{base_dir}/{source_lang}-{target_lang}-vec.path', f'{base_dir}/{source_lang}-{target_lang}-vec.txt'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', required=True, help='Source subtitle file.')
    parser.add_argument('-t', '--target', required=True, help='Target subtitle file.')
    parser.add_argument('-i', '--ignore-empty', required=False, action='store_true',
                        help='Don\'t print subtitles with no valid content.')
    args = parser.parse_args()

    source_sent, source_sent_index = sent_files_for_srt(args.source)
    target_sent, target_sent_index = sent_files_for_srt(args.target)
    if not os.path.exists(source_sent) or not os.path.exists(target_sent):
        run_vecalign(args)

    paths_file, alignments_file = alignment_files(args.source, args.target)
    if not os.path.exists(alignments_file):
        print(f"Failure running vecalign.\nFile does not exist: {alignments_file}")
        exit(1)
    alignments = Alignments(paths_file, source_sent, source_sent_index, target_sent, target_sent_index)
    main(args, alignments)