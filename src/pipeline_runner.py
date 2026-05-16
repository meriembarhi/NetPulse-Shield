import os, sys, subprocess
from pathlib import Path
from typing import Tuple


class PipelineRunner:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.src_dir = self.base_dir / "src"
        self.ai_mode = "rag"

    def _run_script(self, script_name, timeout=300) -> Tuple[bool, str, str]:
        script = self.src_dir / script_name
        if not script.exists():
            return False, "", f"Script not found: {script}"
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(self.base_dir),
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode == 0:
                return True, result.stdout, ""
            return False, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Script timed out ({timeout}s)"
        except Exception as e:
            return False, "", f"Error: {str(e)}"

    def run_clean_data(self) -> Tuple[bool, str, str]:
        return self._run_script("clean_data.py", 300)

    def run_detector(self) -> Tuple[bool, str, str]:
        return self._run_script("detector.py", 600)

    def run_solver(self) -> Tuple[bool, str, str]:
        return self._run_script("solver.py", 300)

    def run_remediator(self) -> Tuple[bool, str, str]:
        return self._run_script("remediator.py", 300)

    def run_report(self, mode="rag") -> Tuple[bool, str, str]:
        if mode == "ollama":
            success1, out1, err1 = self.run_solver()
            success2, out2, err2 = self.run_remediator()
            combined_out = (out1 or "") + "\n" + (out2 or "")
            combined_err = (err1 or "") + "\n" + (err2 or "")
            return success1 or success2, combined_out, combined_err
        return self.run_solver()

    def run_full_pipeline(self, mode="rag") -> Tuple[bool, str, str]:
        log = "STARTING FULL PIPELINE\n\n"
        log += "=" * 60 + "\nSTEP 1: Cleaning Data\n" + "=" * 60 + "\n"
        s, o, e = self.run_clean_data()
        log += o or e
        if not s:
            return False, log + "\nPipeline stopped at data cleaning.\n", e
        log += "\nData cleaning done.\n\n"
        log += "=" * 60 + "\nSTEP 2: Anomaly Detection\n" + "=" * 60 + "\n"
        s, o, e = self.run_detector()
        log += o or e
        if not s:
            return False, log + "\nPipeline stopped at detection.\n", e
        log += "\nDetection done.\n\n"
        log += "=" * 60 + f"\nSTEP 3: AI Report ({mode.upper()})\n" + "=" * 60 + "\n"
        s, o, e = self.run_report(mode)
        log += o or e
        if s:
            log += "\nReport generated.\n\n"
        log += "\n" + "=" * 60 + "\nPIPELINE COMPLETE\n" + "=" * 60 + "\n"
        return True, log, e if not s else ""
