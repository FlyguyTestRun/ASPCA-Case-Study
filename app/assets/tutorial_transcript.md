# Audio walkthrough transcript

Candid field notes from building and testing this system, not a marketing tour. Narration is generated from this transcript with Windows speech synthesis as a placeholder; Bryan replaces it with his own recording (see `app/assets/README.md`).

---

Here is what actually happened when I put this system through its paces, not the pitch version.

The original skill looked fine on a read-through. It reads badly once you run it. I hand-checked the fifty-donor table myself first and found three donors whose tier did not match their own giving history. When the validator ran the same file, it found four. The fourth one, Shirley Magnusdottir, filed as Silver with twenty-two thousand dollars in lifetime giving, is the exact kind of mismatch a careful read misses and a computed check never does.

The date logic was the other trap. One donor had a gift dated a year later than every other record in the file. Nothing in the original skill said what today even meant, so that donor's loyalty bonus would silently change depending on when you happened to run the letters. Fixing it took one line: an explicit reference date in the campaign settings, checked against every gift.

I also audited the source table itself before trusting my own instincts about it. The arithmetic in the original file was fine. Every largest gift, every lifetime total, every last-gift year added up correctly on its own. The real defects were the tier labels and the dates, not the math. That distinction matters, because it tells you where validation effort actually pays off, and it is not where I expected.

The rest is standard engineering discipline applied where the original skill had none. Every letter is checked against a schema before it becomes HTML, not after. Every donor record gets a confidence score, and anything under ninety percent is held for a person to look at before it goes anywhere. Every approved fix, every adopted style choice, every sign-off writes its own dated decision record, the same way an engineering team keeps a change log.

Nothing here sends anything. You review, you approve, you stay in charge.
