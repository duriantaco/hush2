from hush2.utils.scanning import scan_file, shannon_entropy


class TestShannonEntropy:
    def test_low_entropy(self):
        assert shannon_entropy("aaaaaaa") < 1.0

    def test_high_entropy(self):
        assert shannon_entropy("a8f3k2j4h5g6d7s8") > 3.5

    def test_empty(self):
        assert shannon_entropy("") == 0.0


class TestScanFile:
    def test_exact_match(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('TOKEN = "sk-live-abc123"\n')
        findings = scan_file(f, known_secrets={"TOKEN": "sk-live-abc123"})
        assert len(findings) == 1
        assert findings[0].secret_name == "TOKEN"
        assert findings[0].kind == "exact"

    def test_no_match(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        findings = scan_file(f, known_secrets={"KEY": "verysecret"})
        assert len(findings) == 0

    def test_short_secret_skipped(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('x = "ab"\n')
        findings = scan_file(f, known_secrets={"K": "ab"})
        assert len(findings) == 0  # too short

    def test_entropy_detection(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('api_key = "a8f3k2j4h5g6d7s8a9f0k2j4"\n')
        findings = scan_file(f, check_entropy=True, entropy_threshold=3.5)
        entropy_findings = [f for f in findings if f.kind == "entropy"]
        assert len(entropy_findings) >= 1

    def test_skip_binary(self, tmp_path):
        f = tmp_path / "test.png"
        f.write_bytes(b"\x89PNG\r\n")
        findings = scan_file(f, known_secrets={"K": "secret"})
        assert len(findings) == 0
