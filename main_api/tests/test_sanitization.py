from django.test import SimpleTestCase
from main_api.sanitization import sanitize_agent_input


class SanitizationTests(SimpleTestCase):
    """
    Tests for the core sanitization utility that protects against
    prompt injection, steganography, and token bombs.
    """

    def test_esoteric_encoding_nfkc(self):
        """Test that NFKC normalization defeats stylized character bypasses (Bubble text)."""
        bubble_text = "ⓑⓤⓑⓑⓛⓔ"
        sanitized = sanitize_agent_input(bubble_text, apply_nfkc=True)
        self.assertEqual(sanitized, "bubble")

    def test_invisible_steganography_tags(self):
        """Test that Unicode Tags Block (steganography carrier) is stripped."""
        # Unicode Tags Block: U+E0000 to U+E007F
        invisible_tag_text = "Hello\U000e0041World"  # Includes tag for 'A'
        sanitized = sanitize_agent_input(invisible_tag_text)
        self.assertEqual(sanitized, "HelloWorld")

    def test_zalgo_combining_marks_pruning(self):
        """Test that excessive combining marks (Zalgo) are pruned while preserving the start."""
        marks = "\u0300\u0301\u0302\u0303\u0304"
        zalgo_text = "H" + marks + "i"
        sanitized = sanitize_agent_input(zalgo_text)
        # Should keep only the first 2 marks: \u0300\u0301
        self.assertEqual(sanitized, "H\u0300\u0301i")

    def test_token_bomb_zwj_vs_pruning(self):
        """Test that excessive Zero-Width Joiners and Variation Selectors are pruned."""
        # 5 ZWJs
        zwj_bomb = "A" + "\u200d" * 5 + "B"
        sanitized_zwj = sanitize_agent_input(zwj_bomb)
        self.assertEqual(sanitized_zwj, "A\u200d\u200dB")

        # 10 Variation Selectors
        vs_bomb = "🚀" + "\ufe0f" * 10
        sanitized_vs = sanitize_agent_input(vs_bomb)
        self.assertEqual(sanitized_vs, "🚀\ufe0f\ufe0f")

    def test_math_notation_preservation(self):
        """Test that mathematical notation is preserved in loose mode (apply_nfkc=False)."""
        # Mathematical Bold Script Capital A: U+1D4D0
        math_text = "\U0001d4d0 = mc\u00b2"

        # Loose mode should preserve the script letter and superscript 2
        sanitized_loose = sanitize_agent_input(math_text, apply_nfkc=False)
        self.assertEqual(sanitized_loose, math_text)

        # Strict mode (NFKC) will normalize them to basic ASCII
        sanitized_strict = sanitize_agent_input(math_text, apply_nfkc=True)
        self.assertNotEqual(sanitized_strict, math_text)
        self.assertEqual(sanitized_strict, "A = mc2")
