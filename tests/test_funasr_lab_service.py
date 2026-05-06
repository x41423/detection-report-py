import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from backend.funasr_lab.service import FunASRLabConfig, FunASRLabService
from backend.services.asr_provider import AsrTranscriptionResult


class FunASRLabServiceTests(unittest.TestCase):
    @patch("backend.funasr_lab.service.save_config")
    @patch("backend.funasr_lab.service.load_config")
    def test_record_tracking_entry_merges_same_name_and_unit_per_day(self, mocked_load_config, mocked_save_config):
        mocked_load_config.return_value = {
            "funasr_lab_daily_tracking": {
                "records": {
                    "2026-04-21": [
                        {
                            "id": "track-1",
                            "raw_name": "\u5c0f\u571f\u8c46",
                            "normalized_name": "\u571f\u8c46",
                            "unit": "\u65a4",
                            "quantity": 2,
                            "category": "vegetable",
                            "transcript": "\u571f\u8c46\u4e24\u65a4",
                            "source": "funasr-lab",
                            "merge_count": 1,
                            "created_at": "2026-04-21 10:00:00",
                            "updated_at": "2026-04-21 10:00:00",
                        }
                    ]
                }
            }
        }
        service = FunASRLabService()

        result = service.record_tracking_entry(
            intake_date="2026-04-21",
            raw_name="\u5927\u571f\u8c46",
            normalized_name="\u571f\u8c46",
            unit="\u65a4",
            quantity=3,
            category="vegetable",
            transcript="\u571f\u8c46\u4e09\u65a4",
        )

        self.assertTrue(result["merged"])
        self.assertEqual(result["selected_day"]["total_count"], 1)
        self.assertEqual(result["selected_day"]["merge_event_count"], 2)
        self.assertEqual(result["selected_day"]["items"][0]["quantity"], 5.0)
        mocked_save_config.assert_called_once()

    def test_parse_qwen_output_extracts_language_and_text(self):
        service = FunASRLabService()

        language, transcript = service._parse_qwen_output(
            "language Chinese<asr_text>\u767d\u83dc\u56db\u65a4",
            forced_language=None,
        )

        self.assertEqual(language, "Chinese")
        self.assertEqual(transcript, "\u767d\u83dc\u56db\u65a4")

    def test_parse_qwen_output_respects_forced_language(self):
        service = FunASRLabService()

        language, transcript = service._parse_qwen_output(
            "\u767d\u83dc\u56db\u65a4",
            forced_language="chinese",
        )

        self.assertEqual(language, "Chinese")
        self.assertEqual(transcript, "\u767d\u83dc\u56db\u65a4")

    def test_build_context_prompt_uses_memory_and_extra_context(self):
        service = FunASRLabService()
        config = FunASRLabConfig(
            use_domain_context=True,
            extra_context="Today's supplier is A.",
        )

        with patch.object(
            service,
            "_load_lab_memory",
            return_value={
                "recent_hotwords": ["\u9ec4\u74dc"],
                "name_unit_memory": [
                    {
                        "alias": "\u5c0f\u571f\u8c46",
                        "canonical_name": "\u571f\u8c46",
                        "unit": "\u65a4",
                        "updated_at": "2026-04-21 12:00:00",
                        "use_count": 2,
                    }
                ],
            },
        ), patch.object(
            service,
            "_load_manual_hotword_config",
            return_value={
                "manual_hotwords": ["\u897f\u7ea2\u67ff"],
                "name_unit_memory": [],
                "path": "unused",
            },
        ):
            prompt = service._build_context_prompt(config)

        self.assertIn("\u9ec4\u74dc", prompt)
        self.assertIn("\u897f\u7ea2\u67ff", prompt)
        self.assertIn("\u5c0f\u571f\u8c46 -> \u571f\u8c46 (\u65a4)", prompt)
        self.assertIn("Today's supplier is A.", prompt)

    @patch("backend.funasr_lab.service.save_config")
    @patch("backend.funasr_lab.service.load_config")
    def test_remember_recent_usage_does_not_persist_parse_name_unit_memory(self, mocked_load_config, mocked_save_config):
        mocked_load_config.return_value = {
            "funasr_lab_memory": {
                "recent_hotwords": [],
                "name_unit_memory": [],
            }
        }
        service = FunASRLabService()

        service._remember_recent_usage(
            user_hotword=None,
            parse_payload={
                "parse_status": "parsed",
                "draft_name": "\u5c0f\u571f\u8c46",
                "normalized_name": "\u571f\u8c46",
                "unit": "\u65a4",
            },
        )

        mocked_save_config.assert_not_called()

    def test_correction_lifecycle_gates_prompt_context(self):
        with TemporaryDirectory() as temp_dir:
            service = FunASRLabService()
            service.correction_store_path = Path(temp_dir) / "funasr_lab_corrections.json"
            config = FunASRLabConfig(use_domain_context=True)

            with patch.object(
                service,
                "_load_lab_memory",
                return_value={"recent_hotwords": [], "name_unit_memory": []},
            ), patch.object(
                service,
                "_load_manual_hotword_config",
                return_value={"manual_hotwords": [], "name_unit_memory": [], "path": "unused"},
            ):
                candidate = service.create_lexicon_candidate(
                    alias="\u8c46\u4ed8",
                    canonical_name="\u8c46\u8150",
                    unit="\u677f",
                    raw_transcript="\u8c46\u4ed8\u4e24\u677f",
                )
                entry_id = candidate["entry"]["id"]
                self.assertEqual(candidate["entry"]["status"], "pending")
                self.assertNotIn("\u8c46\u4ed8 -> \u8c46\u8150 (\u677f)", service._build_context_prompt(config))

                service.confirm_lexicon_entries(ids=[entry_id])
                self.assertNotIn("\u8c46\u4ed8 -> \u8c46\u8150 (\u677f)", service._build_context_prompt(config))

                applied = service.apply_incremental_lexicon(scope="all_confirmed")
                self.assertEqual(applied["activated_total"], 1)
                self.assertIn("\u8c46\u4ed8 -> \u8c46\u8150 (\u677f)", service._build_context_prompt(config))

                applied_again = service.apply_incremental_lexicon(scope="all_confirmed")
                self.assertEqual(applied_again["activated_total"], 0)
                self.assertEqual(applied_again["lexicon_version"], applied["lexicon_version"])

                service.disable_lexicon_entries(ids=[entry_id], reason="bad correction")
                self.assertNotIn("\u8c46\u4ed8 -> \u8c46\u8150 (\u677f)", service._build_context_prompt(config))

    def test_create_pending_correction_from_parse_does_not_activate_prompt(self):
        with TemporaryDirectory() as temp_dir:
            service = FunASRLabService()
            service.correction_store_path = Path(temp_dir) / "funasr_lab_corrections.json"
            config = FunASRLabConfig(use_domain_context=True)

            with patch.object(
                service,
                "_load_lab_memory",
                return_value={"recent_hotwords": [], "name_unit_memory": []},
            ), patch.object(
                service,
                "_load_manual_hotword_config",
                return_value={"manual_hotwords": [], "name_unit_memory": [], "path": "unused"},
            ):
                candidate = service._create_pending_correction_from_parse(
                    parse_payload={
                        "parse_status": "parsed",
                        "draft_name": "\u9752\u7126",
                        "normalized_name": "\u9752\u6912",
                        "unit": "\u65a4",
                    },
                    raw_transcript="\u9752\u7126\u4e09\u65a4",
                )

                self.assertIsNotNone(candidate)
                self.assertEqual(candidate["entry"]["status"], "pending")
                self.assertNotIn("\u9752\u7126 -> \u9752\u6912 (\u65a4)", service._build_context_prompt(config))

    def test_export_training_pack_is_text_only_and_marks_exported(self):
        with TemporaryDirectory() as temp_dir:
            service = FunASRLabService()
            service.correction_store_path = Path(temp_dir) / "funasr_lab_corrections.json"
            service.training_export_dir = Path(temp_dir)

            candidate = service.create_lexicon_candidate(
                alias="\u8c46\u4ed8",
                canonical_name="\u8c46\u8150",
                unit="\u677f",
                raw_transcript="\u8c46\u4ed8\u4e24\u677f",
                corrected_transcript="\u8c46\u8150\u4e24\u677f",
            )
            entry_id = candidate["entry"]["id"]
            service.confirm_lexicon_entries(ids=[entry_id])
            service.apply_incremental_lexicon(scope="all_confirmed")

            exported = service.export_lexicon_training_pack()

            self.assertEqual(exported["exported_total"], 1)
            export_path = Path(exported["path"])
            self.assertTrue(export_path.exists())
            [line] = export_path.read_text(encoding="utf-8").splitlines()
            record = json.loads(line)
            self.assertEqual(record["alias"], "\u8c46\u4ed8")
            self.assertEqual(record["canonical_name"], "\u8c46\u8150")
            self.assertNotIn("audio_path", record)
            self.assertNotIn("audio_ref", record)

            store = service._load_correction_store()
            self.assertEqual(store["entries"][0]["status"], "active")
            self.assertTrue(store["entries"][0]["exported_at"])
            self.assertEqual(service.lexicon_status()["counts"]["exported"], 1)

    def test_opt_in_audio_retention_adds_audio_ref_to_export(self):
        with TemporaryDirectory() as temp_dir:
            service = FunASRLabService()
            service.correction_store_path = Path(temp_dir) / "funasr_lab_corrections.json"
            service.training_export_dir = Path(temp_dir)

            candidate = service._create_pending_correction_from_parse(
                parse_payload={
                    "parse_status": "parsed",
                    "draft_name": "\u9752\u7126",
                    "normalized_name": "\u9752\u6912",
                    "unit": "\u65a4",
                },
                raw_transcript="\u9752\u7126\u4e09\u65a4",
                retain_audio=True,
                file_bytes=b"fake-audio",
                filename="clip.webm",
                content_type="audio/webm",
            )

            self.assertIsNotNone(candidate)
            entry = candidate["entry"]
            self.assertTrue(entry["audio_ref"].startswith("audio/"))
            self.assertTrue((Path(temp_dir) / entry["audio_ref"]).exists())

            service.confirm_lexicon_entries(ids=[entry["id"]])
            exported = service.export_lexicon_training_pack(statuses=["confirmed"])
            [line] = Path(exported["path"]).read_text(encoding="utf-8").splitlines()
            record = json.loads(line)

            self.assertEqual(record["audio_ref"], entry["audio_ref"])
            self.assertEqual(record["audio_content_type"], "audio/webm")
            self.assertNotIn("audio_path", record)

    def test_manual_hotword_jsonc_config_is_loaded(self):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "funasr_lab_hotwords.jsonc"
            config_path.write_text(
                '{\n'
                '  // comment\n'
                '  "manual_hotwords": ["\u83b2\u85d5", "\u897f\u7ea2\u67ff"],\n'
                '  "name_unit_memory": [\n'
                '    {"alias": "\u756a\u8304", "canonical_name": "\u897f\u7ea2\u67ff", "unit": "\u65a4"}\n'
                '  ]\n'
                '}\n',
                encoding="utf-8",
            )

            service = FunASRLabService()
            service.manual_hotword_config_path = config_path

            loaded = service._load_manual_hotword_config()

        self.assertEqual(loaded["manual_hotwords"], ["\u83b2\u85d5", "\u897f\u7ea2\u67ff"])
        self.assertEqual(loaded["name_unit_memory"][0]["alias"], "\u756a\u8304")

    @patch("backend.funasr_lab.service.importlib.metadata.version", return_value="0.0.6")
    @patch("backend.funasr_lab.service.importlib.util.find_spec", return_value=SimpleNamespace())
    def test_status_reports_qwen_provider(self, _mock_find_spec, _mock_version):
        service = FunASRLabService()

        payload = service.status()

        self.assertEqual(payload["provider"], "qwen3-asr")
        self.assertEqual(payload["defaults"]["model"], "Qwen/Qwen3-ASR-1.7B")

    @patch("backend.funasr_lab.service.AutoProcessor", create=True)
    def test_model_cache_key_uses_model_and_device(self, _mock_auto_processor):
        service = FunASRLabService()
        config = FunASRLabConfig(model="Qwen/Qwen3-ASR-1.7B", device="cuda:0")

        cache_key = service._model_cache_key(config)

        self.assertEqual(cache_key, ("Qwen/Qwen3-ASR-1.7B", "cuda:0"))

    def test_transcribe_audio_reuses_production_qwen_provider(self):
        service = FunASRLabService()
        config = FunASRLabConfig(
            model="Qwen/Qwen3-ASR-1.7B",
            device="cpu",
            language="Chinese",
            max_new_tokens=64,
            use_domain_context=True,
            extra_context="supplier context",
        )
        provider_result = AsrTranscriptionResult(
            transcript="白菜三斤",
            provider="qwen3-asr",
            model=config.model,
            duration_ms=321,
            raw_metadata={
                "raw_text": "白菜三斤",
                "language": "Chinese",
                "device": "cpu",
            },
        )

        with (
            patch.object(service, "is_dependency_available", return_value=True),
            patch.object(service, "_build_context_prompt", return_value="lab prompt") as build_prompt,
            patch.object(service._qwen_provider, "transcribe_audio_with_options", return_value=provider_result) as qwen,
        ):
            result = service.transcribe_audio(
                config=config,
                file_bytes=b"audio",
                filename="clip.webm",
                content_type="audio/webm",
            )

        build_prompt.assert_called_once_with(config)
        qwen.assert_called_once()
        kwargs = qwen.call_args.kwargs
        self.assertEqual(kwargs["model"], config.model)
        self.assertEqual(kwargs["device"], "cpu")
        self.assertEqual(kwargs["language"], "Chinese")
        self.assertEqual(kwargs["max_new_tokens"], 64)
        self.assertFalse(kwargs["use_domain_context"])
        self.assertEqual(kwargs["context_prompt_override"], "lab prompt")
        self.assertEqual(result["asr"]["transcript"], "白菜三斤")
        self.assertEqual(result["asr"]["duration_ms"], 321)


if __name__ == "__main__":
    unittest.main()
