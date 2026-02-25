import unittest
from research.loop.schemas_research import ResearchProposal

class TestResearchSchema(unittest.TestCase):

    def setUp(self):
        self.registry = {
            "allowed_strategies": ["trend_follow"],
            "allowed_symbols": ["BTCUSDT"],
            "allowed_timeframes": ["1h"],
            "parameter_ranges": {"vol_mult": [0.5, 2.0]},
            "forbidden_keywords": ["unhedged"]
        }

    def test_valid_proposal(self):
        p = ResearchProposal(
            experiment_id="EXP_1",
            priority="HIGH",
            hypothesis="Test",
            strategy="trend_follow",
            symbol="BTCUSDT",
            timeframe="1h",
            parameters={"vol_mult": 1.2},
            reasoning="Valid reasoning"
        )
        self.assertTrue(p.validate_registry(self.registry))

    def test_invalid_strategy(self):
        p = ResearchProposal(
            experiment_id="EXP_2",
            priority="LOW",
            hypothesis="Test",
            strategy="invalid_strat",
            symbol="BTCUSDT",
            timeframe="1h",
            parameters={},
            reasoning="Reasoning"
        )
        with self.assertRaises(ValueError) as cm:
            p.validate_registry(self.registry)
        self.assertIn("Strategy", str(cm.exception))

    def test_out_of_range_parameter(self):
        p = ResearchProposal(
            experiment_id="EXP_3",
            priority="MED",
            hypothesis="Test",
            strategy="trend_follow",
            symbol="BTCUSDT",
            timeframe="1h",
            parameters={"vol_mult": 5.0},
            reasoning="Reasoning"
        )
        with self.assertRaises(ValueError) as cm:
            p.validate_registry(self.registry)
        self.assertIn("out of range", str(cm.exception))

    def test_forbidden_keyword(self):
        p = ResearchProposal(
            experiment_id="EXP_4",
            priority="HIGH",
            hypothesis="This is unhedged",
            strategy="trend_follow",
            symbol="BTCUSDT",
            timeframe="1h",
            parameters={},
            reasoning="Reasoning"
        )
        with self.assertRaises(ValueError) as cm:
            p.validate_registry(self.registry)
        self.assertIn("Forbidden keyword", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
