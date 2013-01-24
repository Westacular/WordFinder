#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2012, Wesley Campaigne. All rights reserved.
#

import wordtool
import sys
import traceback
import argparse
import textwrap


def main(arguments=None):
    '''Command-line tool that exposes the word-finding capabilities of the wordtool class.'''

    parser = argparse.ArgumentParser(
        description="Find words in the dictionary that meet various letter-based constraints.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-v", "--verbose", help="increase output verbosity",
        action="store_true")

    parser.add_argument("-c", "--countonly", help="output number of words found, and not the words themselves",
        action="store_true")

    def valid_sort_string(string):
        import re
        m = re.match('^[aAlLr]+$', string)
        if not m:
            raise argparse.ArgumentTypeError("'" + string + "' is not a valid sort specifier. "
                "Expected a combination of 'a', 'A', 'l', 'L', and/or 'r'.")
        return string

    def rewrap_arg_help(text, width=56):
        return textwrap.fill(textwrap.dedent(text), width)

    parser.add_argument("-s", "--sort", type=valid_sort_string,
        help=textwrap.dedent("""\
            sort order for output words:
              'a' for alphabetical (ascending),
              'A' for alphabetical (descending),
              'l' for length (ascending),
              'L' for length (descending),
              'r' to reverse the order"""))

    parser.add_argument("-d", "--dictionary", type=argparse.FileType('r'), metavar="FILENAME",
        help="dictionary file to search within (use '-' for stdin)")

    parser.add_argument("-o", "--output", type=argparse.FileType('w'), metavar="FILENAME",
        default=sys.stdout,
        help="write results to this file (instead of stdout)")

    group = parser.add_argument_group("Filtering arguments",
        rewrap_arg_help(width=74, text='''\
            Each of these arguments is optional. If an argument is unspecified or
            empty, the corresponding constraint is not applied. Note that for the -a,
            -l, and -i options, the number of occurences of a given letter in the
            option string is used to indicate the number of allowed or required
            occurences of that letter in a word.'''))

    group_avail_restr = group.add_mutually_exclusive_group()

    group_avail_restr.add_argument("-a", "--available", default="",
        help=rewrap_arg_help('''\
            the letters that are available for constructing words;
            words must contain only a subset of the letters
            specified here (all other letters are assumed to be
            excluded) (conflicts with -l)'''))

    group_avail_restr.add_argument("-l", "--limited", default="",
        help=rewrap_arg_help('''\
            letters of which there is a limited supply; all other
            letters are assumed to be available and unlimited
            unless excluded with the -x option (conflicts with -a)'''))

    group.add_argument("-x", "--exclude", default="",
        help="letters to exclude: words must contain none of these")

    group.add_argument("-i", "--include", default="",
        help="letters to include: words must contain all of these")

    group.add_argument("-p", "--pattern", default="", metavar="REGULAR_EXPRESSION",
        help="words must match this regular expression")

    group.add_argument("--min", type=int, default=0, metavar="MIN_LENGTH",
        help="minimum length of word to find")

    group.add_argument("--max", type=int, default=0, metavar="MAX_LENGTH",
        help="maximum length of word to find")

    if arguments:
        if isinstance(arguments, list):
            args = parser.parse_args(arguments)
        elif isinstance(arguments, str):
            args = parser.parse_args(arguments.split())
        else:
            raise TypeError("'arguments' must be either a string or a list of strings")
    else:
        args = parser.parse_args()

    t = wordtool.WordTool()
    if args.dictionary:
        t.read_dictionary_from(args.dictionary)

    t.available_letters  = args.available
    t.limited_letters    = args.limited
    t.excluded_letters   = args.exclude
    t.included_letters   = args.include
    t.pattern            = args.pattern
    t.min_length         = args.min
    t.max_length         = args.max

    if args.verbose:
        print >> sys.stderr, "Using dictionary: " + t.dictionary_file
        print >> sys.stderr, "Available letters: " + t.available_letters
        print >> sys.stderr, "Limited letters: " + t.limited_letters
        print >> sys.stderr, "Excluded letters: " + t.excluded_letters
        print >> sys.stderr, "Included letters: " + t.included_letters
        print >> sys.stderr, "Words must match: " + t.pattern
        print >> sys.stderr, "Minimum length: " + str(t.min_length)
        if t.max_length:
            print >> sys.stderr, "Maximum length: " + str(t.max_length)
        else:
            print >> sys.stderr, "No maximum length set."
        print >> sys.stderr, "Finding words..."

    words = t.find_words()

    if args.verbose:
        print >> sys.stderr, str(len(words)) + " words found\n"

    if args.countonly:
        args.output.write(str(len(words)) + "\n")
    else:
        if args.sort:
            from functools import partial
            actions = {
                'a': words.sort,
                'A': partial(words.sort, reverse=True),
                'l': partial(words.sort, key=len),
                'L': partial(words.sort, key=len, reverse=True),
                'r': words.reverse
            }
            for c in args.sort:
                actions[c]()

        args.output.write("\n".join(words) + "\n")
        # args.output.close()


if __name__=='__main__':
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt, e:
        raise e
    except SystemExit, e:
        raise e
    except Exception, e:
        print str(e)
        traceback.print_exc()
        sys.exit(1)
