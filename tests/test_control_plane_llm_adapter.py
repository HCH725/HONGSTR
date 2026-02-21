from hongstr.control_plane.llm import LocalOllamaLLM, NullLLM, build_llm_from_env


class _DummyResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_build_llm_from_env_ollama_default(monkeypatch):
    monkeypatch.setenv("HONGSTR_LLM_MODE", "ollama")
    monkeypatch.delenv("HONGSTR_LLM_ENDPOINT", raising=False)
    monkeypatch.setenv("HONGSTR_LLM_MODEL", "qwen2.5:7b")

    llm, mode = build_llm_from_env()
    assert mode == "ollama"
    assert isinstance(llm, LocalOllamaLLM)
    assert llm.endpoint == "http://127.0.0.1:11434"


def test_build_llm_from_env_unknown_mode(monkeypatch):
    monkeypatch.setenv("HONGSTR_LLM_MODE", "unknown")
    llm, mode = build_llm_from_env()
    assert mode == "null"
    assert isinstance(llm, NullLLM)


def test_local_ollama_generate_extracts_message(monkeypatch):
    llm = LocalOllamaLLM(endpoint="http://127.0.0.1:11434", model="qwen2.5:7b")

    def fake_post(url, json, timeout):
        assert url.endswith("/api/chat")
        assert json["model"] == "qwen2.5:7b"
        return _DummyResponse({"message": {"content": '{"status":"WARN","actions":[]}'}})

    monkeypatch.setattr("hongstr.control_plane.llm.requests.post", fake_post)
    out = llm.generate("prompt")
    assert out.startswith('{"status":"WARN"')
