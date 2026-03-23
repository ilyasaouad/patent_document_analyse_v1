from config.settings import AnalyzerConfig, StrictConfig

def test_config_defaults():
    config = AnalyzerConfig()
    assert config.validate() == True
    assert config.DESCRIPTION_PATTERNS == ["description", "describtion"]

def test_config_weights_validation():
    config = AnalyzerConfig(WEIGHT_FINGERPRINT=0.9)
    # Sum will be 0.9 + 0.4 + 0.2 + 0.1 = 1.6
    assert config.validate() == False

def test_strict_config():
    config = StrictConfig()
    assert config.AI_DETECTION_THRESHOLD == 0.55
