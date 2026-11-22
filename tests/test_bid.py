import json
import unittest

from solutionsquery.agents import PERSONAS
from solutionsquery.bid import parse_bid, run_bidding
from tests.fakes import FakeClient


def make_reply(name):
    doc = {
        "title": f"{name}'s plan",
        "summary": f"summary from {name}",
        "approach": ["step a", "step b"],
        "pros": ["fast"],
        "cons": ["risky"],
        "effort": "M",
    }
    return f"Pitch from {name}.\n\n```json\n{json.dumps(doc)}\n```"


class ParseBidTest(unittest.TestCase):
    def test_parses_json_block(self):
        data = parse_bid(make_reply("Atlas"))
        self.assertEqual(data["title"], "Atlas's plan")
        self.assertEqual(data["approach"], ["step a", "step b"])

    def test_fallback_without_json(self):
        data = parse_bid("Just a plain pitch line\nmore text")
        self.assertEqual(data["title"], "Just a plain pitch line")
        self.assertIn("more text", data["summary"])

    def test_fallback_on_broken_json(self):
        data = parse_bid("```json\n{not valid\n```\nFallback title")
        self.assertEqual(data["title"], "Fallback title")


class RunBiddingTest(unittest.TestCase):
    def test_all_personas_bid(self):
        personas = PERSONAS[:3]
        client = FakeClient(by_persona={p.name: make_reply(p.name) for p in personas})
        bids = run_bidding(client, personas, "build me a todo app")
        self.assertEqual(len(bids), 3)
        for bid in bids:
            self.assertTrue(bid.ok)
            self.assertTrue(bid.title.endswith("'s plan"))
            self.assertEqual(bid.effort, "M")

    def test_streams_tokens(self):
        personas = PERSONAS[:2]
        client = FakeClient(by_persona={p.name: make_reply(p.name) for p in personas})
        seen = []
        run_bidding(client, personas, "need", on_agent_token=lambda p, t: seen.append((p.name, t)))
        self.assertTrue(seen)
        self.assertEqual(len(seen), 2)

    def test_error_captured(self):
        class Boom:
            def chat(self, messages, temperature=0.7, on_token=None):
                raise RuntimeError("kaput")

        bids = run_bidding(Boom(), PERSONAS[:1], "need")
        self.assertEqual(len(bids), 1)
        self.assertFalse(bids[0].ok)
        self.assertIn("kaput", bids[0].error)


if __name__ == "__main__":
    unittest.main()
