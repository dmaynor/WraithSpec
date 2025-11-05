# -*- coding: utf-8 -*-
import json
import unittest

from vap_micro import decode, encode, validate


class TestVAPMicro(unittest.TestCase):
    def test_ci1_roundtrip(self):
        ci = (
            "CI1|SID=7E96|P=Violator-Actual|"
            "HdrC=SENTINEL:7E96:(<UUID>|Violator-Actual|<UTC>|i:[<i>]|2i:[<2i>]|T:<#>|S:<#>)|"
            "HdrF=Stack:Violator-Actual;Ts:<UTC>;Model:GPT-5;SENTINEL:7E96"
        )
        obj = decode(ci)
        self.assertEqual(obj.kind, "CI1")
        self.assertEqual(obj.data["Profile"], "Violator-Actual")
        # encode minimal subset
        micro = encode("CI1", {
            "SID": "7E96",
            "P": "Violator-Actual",
            "HdrC": "X",
            "HdrF": "Stack:Violator-Actual;Ts:<UTC>"
        })
        self.assertTrue(micro.startswith("CI1|"))

    def test_cip2_decode(self):
        cip = (
            "CIP2|SID=7E96|P=Violator-Actual|CTX=GhostInTheShellSAC|"
            "TASK=analyze_outfit_symbolism|CONS=concise+accurate+traced|"
            "TONE=analytical|OUT=essay+trace|REQ=Trace,Ledger,Decision,Critique|MAX=400"
        )
        obj = decode(cip)
        self.assertEqual(obj.kind, "CIP2")
        prompt = obj.data["Prompt"]
        self.assertIn("Trace", prompt["Request"])
        self.assertEqual(prompt["Max"], 400)

    def test_validate_reports_missing(self):
        report = validate("CIP2|SID=7E96|P=Violator-Actual|TASK=do_x")
        self.assertFalse(report["ok"])
        self.assertEqual(report["kind"], "CIP2")

    def test_escaping(self):
        micro = encode("CIP2", {
            "SID": "7E96",
            "P": "Violator-Actual",
            "CTX": "A|B;C,D+E=F",
            "TASK": "t"
        })
        # Ensure reserved chars were escaped in encoded line
        self.assertIn(r"\|", micro)
        obj = decode(micro)
        self.assertEqual(obj.data["Prompt"]["Context"], "A|B;C,D+E=F")


if __name__ == "__main__":
    unittest.main()
