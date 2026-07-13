"""Prompt for trajectory summarization.

Adapted from Agent-S's TASK_SUMMARIZATION_PROMPT (gui_agents/s2/memory/procedural_memory.py):
same "what worked / what to avoid" framing, adjusted for a flat step loop instead of Agent-S's
hierarchical manager/worker plan structure, and for text-only reflection on the action log
(no screenshot - this is a cheap post-hoc call, not a visual judgment).
"""


def get_trajectory_summary_prompt(
	task: str, success: bool | None, final_result: str | None, errors: list[str], action_names: list[str]
) -> str:
	outcome = 'succeeded' if success else ('failed' if success is False else 'ended with an unknown outcome')
	errors_section = '\n'.join(f'- {e}' for e in errors) if errors else 'None'
	actions_section = ', '.join(action_names) if action_names else 'None recorded'

	return f'''You are a summarization agent analyzing a completed browser-automation task.
Your summary will be shown to the same agent the next time it attempts a similar task, as a hint.

Task: {task}
Outcome: {outcome}
Final result: {final_result or 'None'}
Actions taken: {actions_section}
Errors encountered:
{errors_section}

Instructions:
1. If the task succeeded, summarize the approach that worked so it can be repeated.
2. If it failed, explain why and suggest what to do differently next time.

**ATTENTION**
1. Be concise: 1-3 sentences for the lesson.
2. Only extract the correct approach - do not include redundant or exploratory steps.
3. The lesson is for another agent, not a human - it must be actionable through the agent's own actions.
4. Don't give high-level advice (e.g. "be more careful") - be specific to this task.'''
