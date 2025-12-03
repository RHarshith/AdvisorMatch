import sqlite3
import re
from collections import Counter
from typing import Set, List

class DomainSpellChecker:
    def __init__(self, db_path: str):
        self.WORDS = Counter()
        self.N = 0
        self.load_vocabulary(db_path)
    
    def load_vocabulary(self, db_path: str):
        """Build vocabulary from database content"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get text from publications
            cursor.execute("SELECT title, abstract FROM publications")
            for title, abstract in cursor.fetchall():
                self.process_text(title)
                if abstract:
                    self.process_text(abstract)
            
            # Get text from professors
            cursor.execute("SELECT interests FROM professors")
            for (interests,) in cursor.fetchall():
                if interests:
                    self.process_text(interests)
            
            conn.close()
            self.N = sum(self.WORDS.values())
            print(f"✓ Spell checker initialized with {len(self.WORDS)} unique words")
            
        except Exception as e:
            print(f"⚠ Failed to initialize spell checker: {e}")

    def process_text(self, text: str):
        """Extract words from text and update counter"""
        words = re.findall(r'\w+', text.lower())
        self.WORDS.update(words)

    def P(self, word: str) -> float: 
        """Probability of `word`."""
        return self.WORDS[word] / self.N

    def correction(self, word: str) -> str: 
        """Most probable spelling correction for word."""
        return max(self.candidates(word), key=self.P)

    def candidates(self, word: str) -> Set[str]: 
        """Generate possible spelling corrections for word."""
        return (self.known([word]) or self.known(self.edits1(word)) or self.known(self.edits2(word)) or [word])

    def known(self, words: Set[str]) -> Set[str]: 
        """The subset of `words` that appear in the dictionary of WORDS."""
        return set(w for w in words if w in self.WORDS)

    def edits1(self, word: str) -> Set[str]:
        """All edits that are one edit away from `word`."""
        letters    = 'abcdefghijklmnopqrstuvwxyz'
        splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
        deletes    = [L + R[1:]               for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
        replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
        inserts    = [L + c + R               for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def edits2(self, word: str) -> Set[str]: 
        """All edits that are two edits away from `word`."""
        return (e2 for e1 in self.edits1(word) for e2 in self.edits1(e1))

    def correct_text(self, text: str) -> str:
        """Correct all words in a text string"""
        if not text:
            return ""
        
        # Don't correct short queries that might be acronyms
        if len(text) < 4 and text.upper() == text:
            return text
            
        words = re.findall(r'\w+|[^\w\s]', text, re.UNICODE)
        corrected_words = []
        
        for word in words:
            # Only correct alphabetic words
            if word.isalpha():
                # Check if word is already correct (case-insensitive)
                if word.lower() in self.WORDS:
                    corrected_words.append(word)
                else:
                    # Try to correct
                    corrected = self.correction(word.lower())
                    # Preserve capitalization
                    if word.istitle():
                        corrected = corrected.title()
                    elif word.isupper():
                        corrected = corrected.upper()
                    corrected_words.append(corrected)
            else:
                corrected_words.append(word)
                
        # Reconstruct text (simple join for now, could be better)
        # This is a simplification; a real tokenizer/detokenizer would be better
        # But for search queries, space-separated is usually fine
        return ' '.join(corrected_words)
