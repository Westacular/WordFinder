#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2012, Wesley Campaigne. All rights reserved.
#

import re
import os
from collections import defaultdict

_DEFAULT_DICTIONARY_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'wordlist')
# _DEFAULT_DICTIONARY_FILE = '/usr/share/dict/words'

_EMPTY_DICT = defaultdict(int, zip([chr(x) for x in range(97, 123)], [0]*26))

_LETTER_MAX_COUNT = 100
_UNLIMITED_DICT = defaultdict(int, zip([chr(x) for x in range(97, 123)], [_LETTER_MAX_COUNT]*26))


###### HELPER METHODS ######

def _load_wordlist(filename=''):
    if not filename:
        filename = _DEFAULT_DICTIONARY_FILE

    with open(filename, 'r') as filehandle:
        wordlist = _read_wordlist(filehandle)

    return wordlist


def _read_wordlist(filehandle):
    wordlist = [line.strip() for line in filehandle]
    return wordlist


def _letter_count(word):
    Lc = _EMPTY_DICT.copy()
    for L in word:
        Lc[L] += 1
    return Lc


def _limiting_letter_count(word):
    Lc = _UNLIMITED_DICT.copy()
    for L in word:
        if Lc[L] == _LETTER_MAX_COUNT:
            Lc[L] = 0
        Lc[L] += 1
    return Lc


def _word_is_subset_of(word, letterset):
    Lc = _EMPTY_DICT.copy()
    wildcards_used = 0
    for L in word:
        Lc[L] += 1
        if Lc[L] > letterset[L]:
            # Use one of the wildcards
            wildcards_used += 1
            if wildcards_used > letterset['?']:
                # Note that Lc is only partially filled here
                return False, Lc
    return True, Lc


def _word_contains_at_least(word, letterset, Lc=None):
    if not Lc:
        Lc = _letter_count(word)
    for L in letterset.iterkeys():
        if Lc[L] < letterset[L]:
            return False
    return True


class WordTool(object):
    """A versatile tool for finding words meeting various criteria.
    Useful for solving a variety of word games.

    Methods:
        check_for(word) --  Quickly check if 'word' is present in the dictionary.
                            Returns True if it is.

        find_words()    --  Returns a list containing all the words in the dictionary that
                            satisfy the constraints given by the attributes of the WordTool object.

        read_dictionary_from(filehandle) -- Reads the contents of the open filehandle and uses it
                                            as the dictionary.

    Attributes:
        dictionary_file     --  The name of the dictionary file to use as the source of valid
                                words. Dictionary files are assumed to be plaintext files that
                                list one word per line. Changing this will cause wordlist to be
                                reloaded.

        wordlist            --  A list of words to search within. Defaults to containing the
                                full contents of the dictionary. (You can change wordlist to
                                something custom, but be aware that any subsequent changes to
                                dictionary_file will cause wordlist to be replaced.)

        max_length          --  The maximum length (in characters) of word to search for.

        min_length          --  The minimum length (in characters) of word to search for.

        available_letters   --  Find only words that can be constructed using a subset of
                                the letters present in this string. The number of occurrences
                                of a letter counts. So, for example, if this is set to "acinoort",
                                then "train" and "cartoon" would be among the found words, but
                                "arctic", "caption" would not (arctic has too many c's, and
                                caption has a p's).

                                '?' characters, if present, are treated as wildcards; found words
                                may use as many extra letters not otherwise in available_letters
                                as there are '?' characters in it.

                                If available_letters is set to an empty string, this constraint
                                is inactive, and the letter supply is considered unlimited
                                (except as affected by other constraints).

        limited_letters     --  An alternative to available_letters (both cannot be set at the
                                same time). As with available_letters, words can contain at
                                most the number of occurrences of a letter as there are in the
                                limited_letters string. However, whereas letters that are
                                not in available_letters are treated as unavailable, letters that
                                are not in limited_letters are treated as being of unlimited
                                supply.

        excluded_letters    --  Found words absolutely must not contain any of the letters present
                                in this string.

        included_letters    --  Found words must include all the letters listed in this string.

        pattern             --  Found words must match the regular expression given in this string.

        extra_tests         --  A list containing additional functions to test words against.
                                Each function should take a single argument, the word, and return
                                a boolean value. For a word to be a match, each function must
                                return True for that word.
    """

    def __init__(self, dictionary_file=_DEFAULT_DICTIONARY_FILE):
        self._max_length = 0
        self._effective_max_length = 0
        self._min_length = 0
        self._effective_min_length = 0
        self._available_letters = ''
        self._available_letters_counted = None
        self._limited_letters = ''
        self._excluded_letters = ''
        self._excluded_letters_regex = None
        self._included_letters = ''
        self._included_letters_counted = None
        self._pattern = ''
        self._regex = None
        self.wordlist = []
        self._cache_is_good = False
        self._cached_words = []
        self.extra_tests = []
        self.dictionary_file = dictionary_file

    @property
    def dictionary_file(self):
        return self._dictionary_file

    @dictionary_file.setter
    def dictionary_file(self, value):
        self._cache_is_good = False
        if not value:
            value = _DEFAULT_DICTIONARY_FILE
        self._dictionary_file = value
        self.wordlist = _load_wordlist(value)

    def read_dictionary_from(self, filehandle):
        if not isinstance(filehandle, file):
            raise TypeError('WordTool.read_dictionary_from expects an open file object as its argument')
        self._dictionary_file = filehandle.name
        self.wordlist = _read_wordlist(filehandle)
        filehandle.close()



    @property
    def max_length(self):
        return self._max_length

    @max_length.setter
    def max_length(self, value):
        self._cache_is_good = False
        self._max_length = value
        self._update_effective_max_length()


    @property
    def min_length(self):
        return self._min_length

    @min_length.setter
    def min_length(self, value):
        self._cache_is_good = False
        self._min_length = value
        self._update_effective_min_length()


    def _update_effective_max_length(self):
        if self.max_length and self.available_letters:
            self._effective_max_length = min(self.max_length, len(self.available_letters))
        elif self.available_letters:
            self._effective_max_length = len(self.available_letters)
        elif self.max_length:
            self._effective_max_length = self.max_length
        else:
            self._effective_max_length = 0

    def _update_effective_min_length(self):
        if self.min_length and self.included_letters:
            self._effective_min_length = max(self.min_length, len(self.included_letters))
        elif self.included_letters:
            self._effective_min_length = len(self.included_letters)
        elif self.min_length:
            self._effective_min_length = self.min_length
        else:
            self._effective_min_length = 0


    @property
    def available_letters(self):
        return self._available_letters

    @available_letters.setter
    def available_letters(self, value):
        if value == self._available_letters:
            return
        self._cache_is_good = False
        if self._limited_letters:
            raise AttributeError("available_letters cannot be set when limited_letters is non-empty")
        self._available_letters = value
        if value:
            self._available_letters_counted = _letter_count(value)
        else:
            self._available_letters_counted = None
        self._update_effective_max_length()
        self._update_excluded_letters_regex()


    @property
    def limited_letters(self):
        return self._limited_letters

    @limited_letters.setter
    def limited_letters(self, value):
        if value == self._limited_letters:
            return
        self._cache_is_good = False
        if self._available_letters:
            raise AttributeError("limited_letters cannot be set when available_letters is non-empty")
        self._limited_letters = value
        if value:
            self._available_letters_counted = _limiting_letter_count(value)
        else:
            self._available_letters_counted = None
        self._update_excluded_letters_regex()


    @property
    def excluded_letters(self):
        return self._excluded_letters

    @excluded_letters.setter
    def excluded_letters(self, value):
        self._cache_is_good = False
        self._excluded_letters = value
        self._update_excluded_letters_regex()


    @property
    def included_letters(self):
        return self._included_letters

    @included_letters.setter
    def included_letters(self, value):
        self._cache_is_good = False
        self._included_letters = value
        if value:
            self._included_letters_counted = _letter_count(value)
        else:
            self._included_letters_counted = None
        self._update_effective_min_length()


    @property
    def pattern(self):
        return self._pattern

    @pattern.setter
    def pattern(self, value):
        self._cache_is_good = False
        self._pattern = value
        if value:
            self._regex = re.compile(value)
        else:
            self._regex = None


    def _update_excluded_letters_regex(self):
        excl_set = set(
            self.excluded_letters if self.excluded_letters else [])

        unavailable_letters = []
        if self.available_letters and self._available_letters_counted['?'] == 0:
            unavailable_letters = [L for L in self._available_letters_counted.iterkeys() if self._available_letters_counted[L] == 0]

        excl_set.update(unavailable_letters)

        if excl_set:
            self._excluded_letters_regex = re.compile('[' + "".join(excl_set) + ']')
        else:
            self._excluded_letters_regex = None


    def check_for(self, word):
        '''Returns True for words that are in the dictionary.'''
        return word in self.wordlist
        # '''(NOTE: Assumes dictionary is already sorted alphabetically.)'''
        # import bisect
        # i = bisect.bisect_left(self.wordlist, word)
        # if i != len(self.wordlist) and self.wordlist[i] == word:
        #     return True
        # return False

    def is_word_valid(self, word):
        '''Returns True if word passes all the tests set for this object'''
        return self.passes_internal_tests(word) and self.passes_extra_tests(word)

    def passes_internal_tests(self, word):
        '''Returns True if word passes all the internal tests set for this object'''
        Lc = None
        if self._effective_min_length and len(word) < self._effective_min_length:
            return False
        if self._effective_max_length and len(word) > self._effective_max_length:
            return False
        if self._regex and not self._regex.search(word):
            return False
        if self._excluded_letters_regex and self._excluded_letters_regex.search(word):
            return False
        if self._available_letters_counted:
            is_subset, Lc = _word_is_subset_of(word, self._available_letters_counted)
            if not is_subset:
                return False
        if self._included_letters_counted and not _word_contains_at_least(word, self._included_letters_counted, Lc):
            return False
        return True

    def passes_extra_tests(self, word):
        '''Returns True if word passes all the extra tests set for this object'''
        for test in self.extra_tests:
            if not test(word):
                return False
        return True

    def find_words(self):
        '''Returns the list of words from the dictionary that satisfy
        the various constraints set by the properties of the object'''
        if not self._cache_is_good:
            self._cached_words = [w for w in self.wordlist if self.passes_internal_tests(w)]
            self._cache_is_good = True

        found_words = [w for w in self._cached_words if self.passes_extra_tests(w)]
        return found_words
