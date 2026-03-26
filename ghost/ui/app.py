"""Ghost UI — Gradio-based control interface.

A clean, investor-ready interface that shows:
- Live screen view with action overlay
- Task input
- Action log with reasoning
- Start/stop controls
"""

import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

import gradio as gr
from PIL import Image, ImageDraw, ImageFont

from ghost.agent.loop import GhostAgent, ActionResult, AgentState
from ghost.agent.screen import ScreenCapture
from ghost.agent.input_control import InputController
from ghost.model.grounding_model import GhostModel


class GhostUI:
    """The presentable frontend for Ghost."""

    def __init__(
        self,
        reasoning_model: Optional[str] = None,
        grounding_model: Optional[str] = None,
        quantization: str = "4bit",
        single_model: bool = False,
    ):
        self.reasoning_model = reasoning_model or "Qwen/Qwen2.5-VL-7B-Instruct"
        self.grounding_model = grounding_model or "OS-Copilot/OS-Atlas-Base-7B"
        self.quantization = quantization
        self.single_model = single_model
        self.agent: Optional[GhostAgent] = None
        self.model: Optional[GhostModel] = None
        self.screen = ScreenCapture()
        self.is_running = False
        self.action_log: list[str] = []
        self.current_screenshot: Optional[Image.Image] = None
        self._agent_thread: Optional[threading.Thread] = None

    def _load_model(self):
        """Load model on first use."""
        if self.model is None:
            self.action_log.append("Loading Ghost brain (reasoning + grounding)...")
            self.model = GhostModel(
                reasoning_model=self.reasoning_model,
                grounding_model=self.grounding_model,
                quantization=self.quantization,
                single_model=self.single_model,
            )
            self.agent = GhostAgent(
                model=self.model,
                screen=self.screen,
                on_action=self._on_action,
                on_step=self._on_step,
            )
            self.action_log.append("Ghost is ready.")

    def _on_action(self, result: ActionResult):
        """Callback when agent takes an action."""
        status = "OK" if result.success else f"FAIL: {result.error}"
        entry = f"[Step {result.step}] {result.action}"
        if result.coordinates:
            entry += f"({result.coordinates[0]}, {result.coordinates[1]})"
        if result.text:
            entry += f" — {result.text}"
        entry += f"  [{status}]"
        if result.reasoning:
            entry += f"\n  Reasoning: {result.reasoning[:120]}"
        self.action_log.append(entry)

    def _on_step(self, step: int, screenshot: Image.Image):
        """Callback at each step — update live view."""
        self.current_screenshot = screenshot

    def _annotate_screenshot(self, screenshot: Image.Image, action: Optional[ActionResult] = None) -> Image.Image:
        """Draw action overlay on screenshot."""
        img = screenshot.copy()
        draw = ImageDraw.Draw(img)

        if action and action.coordinates:
            x, y = action.coordinates
            # Draw crosshair
            r = 15
            draw.ellipse([x - r, y - r, x + r, y + r], outline="red", width=3)
            draw.line([x - r * 2, y, x + r * 2, y], fill="red", width=2)
            draw.line([x, y - r * 2, x, y + r * 2], fill="red", width=2)

            # Label
            label = f"{action.action} ({x},{y})"
            draw.text((x + r + 5, y - 10), label, fill="red")

        return img

    def start_task(self, task: str):
        """Start executing a task."""
        if not task.strip():
            return None, "Please enter a task.", ""

        self._load_model()

        self.is_running = True
        self.action_log = [f"Starting task: {task}"]

        def run():
            try:
                state = self.agent.run(task)
                if state.is_done:
                    self.action_log.append(f"\nTask COMPLETED: {state.result}")
                else:
                    self.action_log.append(f"\nTask INCOMPLETE after {state.current_step} steps")
            except Exception as e:
                self.action_log.append(f"\nERROR: {e}")
            finally:
                self.is_running = False

        self._agent_thread = threading.Thread(target=run, daemon=True)
        self._agent_thread.start()

        return self._get_screenshot_display(), "Running...", self._format_log()

    def stop_task(self):
        """Stop the current task."""
        self.is_running = False
        self.action_log.append("Task stopped by user.")
        return "Stopped.", self._format_log()

    def refresh_view(self):
        """Update the live view."""
        screenshot = self.current_screenshot or self.screen.capture()
        log = self._format_log()
        status = "Running..." if self.is_running else "Idle"
        return screenshot, status, log

    def _get_screenshot_display(self) -> Image.Image:
        """Get the current screen for display."""
        return self.current_screenshot or self.screen.capture()

    def _format_log(self) -> str:
        """Format action log for display."""
        return "\n".join(self.action_log[-50:])  # last 50 entries

    def build_ui(self) -> gr.Blocks:
        """Build the Gradio interface."""
        self._theme = gr.themes.Base(
            primary_hue="red",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        )
        self._css = """
            .ghost-header { text-align: center; margin-bottom: 20px; }
            .ghost-header h1 { font-size: 2.5em; font-weight: 800; color: #dc2626; }
            .ghost-header p { color: #64748b; font-size: 1.1em; }
            .action-log { font-family: 'JetBrains Mono', monospace; font-size: 0.85em; }
        """
        with gr.Blocks(title="Ghost — Autonomous Computer Control") as app:
            gr.HTML("""
                <div class="ghost-header">
                    <h1>GHOST</h1>
                    <p>Autonomous Computer Control — Runs Locally, Sees Your Screen, Acts Like a Human</p>
                </div>
            """)

            with gr.Row():
                with gr.Column(scale=3):
                    screen_view = gr.Image(
                        label="Live Screen",
                        type="pil",
                        interactive=False,
                        height=500,
                    )

                with gr.Column(scale=1):
                    status_box = gr.Textbox(label="Status", value="Idle", interactive=False)

                    task_input = gr.Textbox(
                        label="Task",
                        placeholder="e.g., Open Firefox and search for 'Ghost AI agent'",
                        lines=3,
                    )

                    with gr.Row():
                        start_btn = gr.Button("Start", variant="primary", size="lg")
                        stop_btn = gr.Button("Stop", variant="stop", size="lg")

                    action_log = gr.Textbox(
                        label="Action Log",
                        lines=15,
                        interactive=False,
                        elem_classes=["action-log"],
                    )

            # Auto-refresh timer
            refresh_timer = gr.Timer(1.0)
            refresh_timer.tick(
                fn=self.refresh_view,
                outputs=[screen_view, status_box, action_log],
            )

            # Button handlers
            start_btn.click(
                fn=self.start_task,
                inputs=[task_input],
                outputs=[screen_view, status_box, action_log],
            )
            stop_btn.click(
                fn=self.stop_task,
                outputs=[status_box, action_log],
            )

        return app


def main():
    """Launch Ghost UI."""
    import argparse

    parser = argparse.ArgumentParser(description="Ghost UI")
    parser.add_argument("--reasoning-model", type=str, default="Qwen/Qwen2.5-VL-7B-Instruct")
    parser.add_argument("--grounding-model", type=str, default="OS-Copilot/OS-Atlas-Base-7B")
    parser.add_argument("--single-model", action="store_true", help="Use only reasoning model (lighter, less accurate)")
    parser.add_argument("--quantization", type=str, default="4bit", choices=["4bit", "8bit", "none"])
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true", help="Create public Gradio link")
    args = parser.parse_args()

    quant = None if args.quantization == "none" else args.quantization

    ui = GhostUI(
        reasoning_model=args.reasoning_model,
        grounding_model=args.grounding_model,
        quantization=quant,
        single_model=args.single_model,
    )
    app = ui.build_ui()
    app.launch(server_port=args.port, share=args.share, theme=ui._theme, css=ui._css)


if __name__ == "__main__":
    main()
