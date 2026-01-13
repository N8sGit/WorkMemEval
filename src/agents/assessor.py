"""
WorkMemEval: Assessor Agent

The Assessor Agent represents the benchmark itself as an active agent.
It owns the environment, controls the task flow, and evaluates the Assessee agent
through standardized A2A protocols.

Responsibilities:
1. Environment Ownership: Manages the virtual file system and state.
2. Protocol Management: Sends/receives A2A messages.
3. Dynamic Probing: Injects probes based on real-time state.
4. Outcome Verification: Verifies results by inspecting state (files, git, etc.), not just regex.
"""

import logging
import time
import ast
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..core.a2a import A2AMessage, ActionRequest, ActionResult, MessageType
from ..core.task_specification import TaskSpecification, CheckpointSpecification, MemoryProbe, ProbeType, MemoryPillar
from ..core.action_trace import ActionTracer, ActionType
from ..evaluation.results import CheckpointResult, EvaluationResult
from ..evaluation.test_runner import PytestRunner
from ..evaluation.probe_scheduler import ProbeScheduler, ProbeInjectionTiming
from .secure_file_ops import SecureFileOperations, SecurityViolationError

class AssessorAgent:
    def __init__(self, task_spec: TaskSpecification, working_directory: Path):
        self.task_spec = task_spec
        self.working_directory = working_directory
        self.tracer = None
        
        # Internal components
        self.test_runner = PytestRunner()
        self.probe_scheduler = ProbeScheduler()
        self.file_ops = SecureFileOperations(working_directory)
        
        # State tracking
        self.current_checkpoint_idx = 0
        self.scheduled_probes = {} # Map[checkpoint_id, List[MemoryProbe]]
        self.pending_probes = []   # Probes waiting for their moment in current checkpoint
        self.action_count_in_checkpoint = 0
        
        # Memory Pillar Metrics Tracking
        self.pillar_scores = {
            MemoryPillar.MEMORY_FIDELITY: {"hits": 0, "misses": 0, "total": 0},
            MemoryPillar.CONTEXTUAL_RELEVANCE: {"hits": 0, "misses": 0, "total": 0},
            MemoryPillar.BEHAVIORAL_INTEGRITY: {"hits": 0, "misses": 0, "total": 0}
        }
        self.accessed_distractors = set()
        
        self.environment_state = {
            "files": {},
            "phase": "init",
            "active_probes": []
        }
        
        # Interruption handling
        self.pending_action_result: Optional[A2AMessage] = None
        
        # Setup logging
        self.logger = logging.getLogger("AssessorAgent")

    def initialize_session(self, tracer: ActionTracer):
        """Start the assessment session"""
        self.tracer = tracer
        self.logger.info(f"Initializing assessment for task: {self.task_spec.task_id}")
        
        # Schedule probes using the rigorous logic
        if hasattr(self.task_spec, 'memory_probes') and self.task_spec.memory_probes:
            self.scheduled_probes = self.probe_scheduler.schedule_probes(
                self.task_spec.memory_probes, 
                self.task_spec
            )
            for cp_id, probes in self.scheduled_probes.items():
                self.logger.info(f"DEBUG: Scheduled {len(probes)} probes for {cp_id}")
        
        # Snapshot initial state
        self._snapshot_environment("initial_state")
        
        # Prepare first checkpoint
        self._advance_to_checkpoint(0)
        
        first_cp = self._get_current_checkpoint()
        first_cp_dict = None
        if first_cp:
            # Start tracing the first checkpoint
            if self.tracer:
                self.tracer.start_checkpoint(first_cp.checkpoint_id)
                self.tracer.log_action(
                    ActionType.CHECKPOINT_START, 
                    success=True, 
                    title=first_cp.title
                )

            if hasattr(first_cp, 'to_dict'):
                first_cp_dict = first_cp.to_dict()
            elif is_dataclass(first_cp):
                first_cp_dict = asdict(first_cp)
            else:
                first_cp_dict = first_cp.__dict__
        
        return A2AMessage(
            type=MessageType.TASK_START,
            payload={
                "task_id": self.task_spec.task_id,
                "description": self.task_spec.description,
                "working_directory": str(self.working_directory),
                "working_history": getattr(self.task_spec, 'working_history', []),
                "first_checkpoint": first_cp_dict
            }
        )

    def _advance_to_checkpoint(self, idx: int):
        """Move assessor state to specific checkpoint"""
        if idx >= len(self.task_spec.checkpoints):
            return
            
        self.current_checkpoint_idx = idx
        self.action_count_in_checkpoint = 0
        current_cp = self.task_spec.checkpoints[idx]
        
        # Load probes for this checkpoint
        self.pending_probes = self.scheduled_probes.get(current_cp.checkpoint_id, [])
        
        # Sort by injection timing (Start first)
        if self.pending_probes:
            self.pending_probes.sort(key=lambda p: 0 if self.probe_scheduler.injection_points.get(p.probe_id).timing == ProbeInjectionTiming.CHECKPOINT_START else 1)

    def _get_current_checkpoint(self) -> Optional[CheckpointSpecification]:
        if 0 <= self.current_checkpoint_idx < len(self.task_spec.checkpoints):
            return self.task_spec.checkpoints[self.current_checkpoint_idx]
        return None

    def process_message(self, message: A2AMessage) -> A2AMessage:
        """Process an incoming message from the Assessee"""
        self.logger.debug(f"Received message type: {message.type}")
        
        if message.type == MessageType.ACTION_REQUEST:
            return self._handle_action_request(message)
        elif message.type == MessageType.PROBE_RESPONSE:
            return self._handle_probe_response(message)
        elif message.type == MessageType.CHECKPOINT_COMPLETE:
            return self._handle_checkpoint_completion(message)
        elif message.type == MessageType.TASK_COMPLETE:
            return self._handle_task_completion(message)
        else:
            self.logger.warning(f"Unknown message type: {message.type}")
            return A2AMessage(
                type=MessageType.ENVIRONMENT_UPDATE,
                payload={"status": "error", "message": "Unknown message type"}
            )

    def _handle_checkpoint_completion(self, message: A2AMessage) -> A2AMessage:
        """Handle agent reporting checkpoint completion"""
        checkpoint_id = message.payload.get("checkpoint_id")
        current_cp = self._get_current_checkpoint()
        
        self.logger.info(f"DEBUG: Handling completion for {checkpoint_id}. Current expected: {current_cp.checkpoint_id if current_cp else 'None'}")
        
        if not current_cp or current_cp.checkpoint_id != checkpoint_id:
            self.logger.warning(f"Received completion for unexpected checkpoint: {checkpoint_id}. Expected: {current_cp.checkpoint_id if current_cp else 'None'}")
            return A2AMessage(type=MessageType.ENVIRONMENT_UPDATE, payload={"status": "error", "message": f"Wrong checkpoint. Expected {current_cp.checkpoint_id}"})

        self.logger.info(f"Verifying checkpoint: {checkpoint_id}")
        print(f"Assessor: Verifying {checkpoint_id} using {current_cp.test_file}")
        
        # 1. Run Verification Tests
        test_result = self.test_runner.run(
            current_cp.test_file,
            self.working_directory
        )
        print(f"Assessor: Test Result for {checkpoint_id}: Passed={test_result.passed} (Exit Code: {test_result.exit_code})")
        if not test_result.passed:
             print(f"Assessor: Test Errors: {test_result.errors}")
        
        # 2. Log Result
        self.tracer.log_action(
            ActionType.CHECKPOINT_COMPLETE,
            success=test_result.passed,
            tests_passed=test_result.passed,
            exit_code=test_result.exit_code,
            checkpoint_id=checkpoint_id
        )
        # Finalize the checkpoint trace
        self.tracer.complete_checkpoint(tests_passed=test_result.passed)
        
        if test_result.passed:
            self.logger.info(f"Checkpoint {checkpoint_id} PASSED")
        else:
            self.logger.info(f"Checkpoint {checkpoint_id} FAILED")

        # 3. Advance to Next Checkpoint
        next_idx = self.current_checkpoint_idx + 1
        if next_idx < len(self.task_spec.checkpoints):
            self._advance_to_checkpoint(next_idx)
            next_cp = self._get_current_checkpoint()
            
            # Start tracing the next checkpoint
            if self.tracer:
                self.tracer.start_checkpoint(next_cp.checkpoint_id)
                self.tracer.log_action(
                    ActionType.CHECKPOINT_START, 
                    success=True, 
                    title=next_cp.title
                )
            
            # Serialize next checkpoint
            next_cp_dict = None
            if hasattr(next_cp, 'to_dict'):
                next_cp_dict = next_cp.to_dict()
            elif is_dataclass(next_cp):
                next_cp_dict = asdict(next_cp)
            else:
                next_cp_dict = next_cp.__dict__

            return A2AMessage(
                type=MessageType.CHECKPOINT_START,
                payload=next_cp_dict
            )
        else:
            # All checkpoints done
            return self._handle_task_completion(message)

    def _handle_action_request(self, message: A2AMessage) -> A2AMessage:
        """Handle a tool use/action request from the assessee"""
        request_data = message.payload
        tool_name = request_data.get("tool_name")
        args = request_data.get("arguments", {})
        req_id = request_data.get("request_id")
        
        # Increment action count for timing
        self.action_count_in_checkpoint += 1
        
        # --- CONTEXTUAL RELEVANCE TRACKING ---
        if tool_name == "read_file":
            file_path = args.get("path") or args.get("file_path")
            if file_path:
                # Normalize path checking
                is_distractor = False
                if hasattr(self.task_spec.repository, 'distractor_files'):
                    is_distractor = any(d in file_path for d in self.task_spec.repository.distractor_files)
                
                if is_distractor:
                    self.pillar_scores[MemoryPillar.CONTEXTUAL_RELEVANCE]["misses"] += 1
                    self.pillar_scores[MemoryPillar.CONTEXTUAL_RELEVANCE]["total"] += 1
                    self.accessed_distractors.add(file_path)
                    self.logger.info(f"DISTRACTOR ACCESSED: {file_path}")
                else:
                    # Reward staying on target
                    self.pillar_scores[MemoryPillar.CONTEXTUAL_RELEVANCE]["hits"] += 1
                    self.pillar_scores[MemoryPillar.CONTEXTUAL_RELEVANCE]["total"] += 1

        # LOGGING: Trace the attempt
        self.tracer.log_action(
            ActionType.COMMAND_EXECUTE, # Generalized action
            file_path=args.get("file_path"),
            metadata={"tool": tool_name, "args": args}
        )

        # EXECUTION: Perform the action in the controlled environment
        # In a real impl, this calls the actual tool (FileWrite, RunCommand)
        # For now, we simulate the environment interaction logic
        success, output = self._execute_tool(tool_name, args)
        
        # Prepare the result message
        action_result_msg = A2AMessage(
            type=MessageType.ACTION_RESULT,
            payload=ActionResult(
                request_id=req_id,
                success=success,
                output=output,
                state_changes=self._get_state_diff()
            ).__dict__
        )
        
        # DYNAMIC PROBING: Check if this action triggers a probe
        # e.g., if writing to 'legacy_processor.py', maybe inject a merge conflict?
        probe = self._check_for_probe_trigger(tool_name, args)
        if probe:
            # INTERRUPTION: Queue the result and inject probe first
            self.logger.info(f"Interrupting action {tool_name} to inject probe {probe.probe_id}")
            self.pending_action_result = action_result_msg
            return self._inject_probe(probe)

        return action_result_msg

    def _handle_probe_response(self, message: A2AMessage) -> A2AMessage:
        """Handle agent's response to a probe"""
        # VERIFICATION: rigorous check
        response_text = message.payload.get("response")
        probe_id = message.payload.get("probe_id")
        
        # Get the probe definition from task spec
        # (Assuming we have a map or search for it)
        probe = next((p for p in self.task_spec.memory_probes if p.probe_id == probe_id), None)
        
        score = 0.0
        if probe:
            score = self._verify_probe_outcome(probe, response_text)
            
            # --- PILLAR SCORING UPDATE ---
            # Update the specific pillar associated with this probe
            if probe.pillar in self.pillar_scores:
                self.pillar_scores[probe.pillar]["total"] += 1
                if score >= 0.5: # Threshold for "hit" / pass
                    self.pillar_scores[probe.pillar]["hits"] += 1
                else:
                    self.pillar_scores[probe.pillar]["misses"] += 1
        else:
            score = 0.0 # Unknown probe
        
        self.tracer.log_action(
            ActionType.MEMORY_PROBE_SCORE,
            metadata={"probe_id": probe_id, "score": score}
        )
        
        # Check if we have a pending action result to release (resume flow)
        if self.pending_action_result:
            self.logger.info("Resuming suspended action after probe interaction")
            result = self.pending_action_result
            self.pending_action_result = None
            return result
        
        return A2AMessage(
            type=MessageType.ENVIRONMENT_UPDATE,
            payload={"status": "probe_evaluated", "score": score}
        )

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, Any]:
        """Execute tool in the sandbox via SecureFileOps"""
        try:
            if tool_name == "read_file":
                path = args.get("path") or args.get("file_path")
                if not path:
                    return False, "Missing 'path' argument"
                content = self.file_ops.read_file(path)
                return True, content
                
            elif tool_name == "write_file":
                path = args.get("path") or args.get("file_path")
                content = args.get("content", "")
                if not path:
                    return False, "Missing 'path' argument"
                self.logger.info(f"DEBUG: Assessor writing to {path}, content len: {len(content)}")
                self.logger.info(f"DEBUG: Content start: {content[:50]}")
                self.file_ops.write_file(path, content)
                return True, "File written successfully"
                
            elif tool_name == "list_files":
                path = args.get("path", ".")
                files = self.file_ops.list_files(path)
                return True, files

            elif tool_name == "file_exists":
                path = args.get("path") or args.get("file_path")
                if not path:
                    return False, "Missing 'path' argument"
                exists = self.file_ops.file_exists(path)
                return True, exists

            elif tool_name == "submit_decision":
                # Special tool for submitting a final decision/answer
                decision = args.get("decision")
                context = args.get("context", {})
                self.logger.info(f"DECISION SUBMITTED: {str(decision)[:100]}...")
                # We could validate it here or just store it
                # For now, just log success
                return True, "Decision recorded"
                
            # TODO: Add safe command execution for 'run_test' etc.
            
            return False, f"Unknown tool: {tool_name}"
            
        except (SecurityViolationError, FileNotFoundError, OSError) as e:
            return False, str(e)

    def _verify_probe_outcome(self, probe: MemoryProbe, response_text: str) -> float:
        """
        Verify probe outcome using STATE inspection (AST, Tests), not just text.
        This enables 'Outcome-valid' evaluation.
        """
        score = 0.0
        
        # 1. Structural Verification (Static Analysis)
        if probe.probe_type == ProbeType.N_BACK_INTEGRATION:
            # Check if code imports/calls the N-back dependency
            score += self._verify_n_back_integration(probe)
            
        elif probe.probe_type == ProbeType.UPDATE_ROBUSTNESS:
            # Check if code changed to reflect new requirement
            score += self._verify_requirement_update(probe)
            
        # 2. Behavioral Verification (Dynamic Analysis)
        # Run a specific test case associated with this probe
        if hasattr(probe, 'verification_test_file'):
            test_result = self.test_runner.run(
                probe.verification_test_file, 
                self.working_directory
            )
            if test_result.passed:
                score += 0.5
                
        # 3. Text-based Verification (Fallback/Augmentation)
        # For synthetic tasks or where AST analysis isn't fully implemented
        text_score = 0.0
        response_lower = response_text.lower()
        
        if probe.probe_type == ProbeType.DISTRACTOR_INJECTION:
            # Check for rejection/ignoring of distractor
            if any(w in response_lower for w in ["ignore", "irrelevant", "stick to", "disregard"]):
                text_score = 1.0
            elif "acknowledged" in response_lower:
                text_score = 0.5
                
        elif probe.probe_type == ProbeType.UPDATE_ROBUSTNESS:
            # Check for acceptance of update
            if any(w in response_lower for w in ["adapt", "ensure", "comply", "update", "apply"]):
                text_score = 1.0
            elif "understood" in response_lower:
                text_score = 0.5
                
        # Use text score if structural/behavioral verification didn't yield results
        if score == 0.0 and text_score > 0.0:
            score = text_score
        elif score == 0.0 and len(response_text) > 10:
             # Minimal credit for acknowledging
             score += 0.1
             
        return min(score, 1.0)

    def _verify_n_back_integration(self, probe: MemoryProbe) -> float:
        """
        AST Analysis: Does the current implementation actually call functions 
        from the N-back dependency?
        """
        # Identify the target file and dependency
        # This would normally come from the probe definition's metadata
        target_file = "calculator.py" # Example
        dependency_func = "previous_func" # Example
        
        file_path = self.working_directory / target_file
        if not file_path.exists():
            return 0.0
            
        try:
            tree = ast.parse(file_path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for function call
                    if isinstance(node.func, ast.Name) and node.func.id == dependency_func:
                        return 0.5 # Found the call
            return 0.0
        except SyntaxError:
            return 0.0

    def _verify_requirement_update(self, probe: MemoryProbe) -> float:
        """
        AST Analysis: Did the logic change?
        """
        # This is harder without a "before" snapshot to compare ASTs, 
        # but we can check for presence of new logic.
        return 0.0

    def _snapshot_environment(self, label: str):
        """Take a snapshot of files/state for diffing"""
        # Scan working directory
        pass

    def _get_state_diff(self) -> Dict[str, Any]:
        """Return what changed since last snapshot"""
        return {}
        if not self.pending_probes:
            return None
            
        # Get the next probe
        probe = self.pending_probes[0]
        
        # Determine if we should trigger based on timing and action count
        injection_point = self.probe_scheduler.injection_points.get(probe.probe_id)
        timing = injection_point.timing if injection_point else ProbeInjectionTiming.MID_CHECKPOINT
        
        should_trigger = False
        
        if timing == ProbeInjectionTiming.CHECKPOINT_START:
            # Trigger almost immediately (e.g. 1st or 2nd action)
            should_trigger = self.action_count_in_checkpoint >= 1
        elif timing == ProbeInjectionTiming.MID_CHECKPOINT:
            # Trigger after some work (e.g. 3rd action)
            should_trigger = self.action_count_in_checkpoint >= 3
        elif timing == ProbeInjectionTiming.CHECKPOINT_END:
            # Trigger late (e.g. 5th action)
            should_trigger = self.action_count_in_checkpoint >= 5
        elif timing == ProbeInjectionTiming.MEMORY_PRESSURE_PEAK:
            # Trigger based on heuristic (e.g. 4th action)
            should_trigger = self.action_count_in_checkpoint >= 4
        else:
            # Default fallback
            should_trigger = self.action_count_in_checkpoint >= 2
            
        if should_trigger:
            self.logger.info(f"Triggering probe {probe.probe_id} at action {self.action_count_in_checkpoint} (Timing: {timing})")
            return self.pending_probes.pop(0)
            

    def _check_for_probe_trigger(self, tool_name: str, args: Dict) -> Optional[Any]:
        """Determine if current state/action triggers an interrupt probe"""
        if not self.pending_probes:
            return None
            
        # Get the next probe
        probe = self.pending_probes[0]
        
        # Determine if we should trigger based on timing and action count
        injection_point = self.probe_scheduler.injection_points.get(probe.probe_id)
        timing = injection_point.timing if injection_point else ProbeInjectionTiming.MID_CHECKPOINT
        
        should_trigger = False
        
        if timing == ProbeInjectionTiming.CHECKPOINT_START:
            # Trigger almost immediately (e.g. 1st or 2nd action)
            should_trigger = self.action_count_in_checkpoint >= 1
        elif timing == ProbeInjectionTiming.MID_CHECKPOINT:
            # Trigger after some work (e.g. 3rd action)
            should_trigger = self.action_count_in_checkpoint >= 3
        elif timing == ProbeInjectionTiming.CHECKPOINT_END:
            # Trigger late (e.g. 5th action)
            should_trigger = self.action_count_in_checkpoint >= 5
        elif timing == ProbeInjectionTiming.MEMORY_PRESSURE_PEAK:
            # Trigger based on heuristic (e.g. 4th action)
            should_trigger = self.action_count_in_checkpoint >= 4
        else:
            # Default fallback
            should_trigger = self.action_count_in_checkpoint >= 2
            
        if should_trigger:
            self.logger.info(f"Triggering probe {probe.probe_id} at action {self.action_count_in_checkpoint} (Timing: {timing})")
            return self.pending_probes.pop(0)
            
        return None

    def _inject_probe(self, probe: Any) -> A2AMessage:
        return A2AMessage(
            type=MessageType.PROBE_INJECTION,
            payload={
                "probe_id": probe.probe_id, 
                "challenge": probe.description,
                "probe_type": str(probe.probe_type.value) if hasattr(probe.probe_type, "value") else str(probe.probe_type),
                "pillar": str(probe.pillar.value) if hasattr(probe.pillar, "value") else str(probe.pillar)
            }
        )

    def _handle_task_completion(self, message: A2AMessage) -> A2AMessage:
        # Calculate final pillar scores
        final_scores = {}
        for pillar, stats in self.pillar_scores.items():
            if stats["total"] > 0:
                final_scores[pillar.value] = stats["hits"] / stats["total"]
            else:
                final_scores[pillar.value] = 0.0 # Default if no events tested this pillar
        
        self.logger.info(f"Task Complete. Pillar Scores: {final_scores}")
        
        # Complete the task trace
        if self.tracer:
            # Assume success if we reached here without fatal error? 
            # Or use message payload status?
            # For benchmark, if we reached the end, it's a completion.
            # Success depends on success criteria which we haven't fully verified yet.
            # But let's mark it as completed execution.
            self.tracer.complete_task(completed_successfully=True)

        return A2AMessage(
            type=MessageType.TASK_COMPLETE,
            payload={
                "status": "acknowledged",
                "pillar_scores": final_scores,
                "accessed_distractors": list(self.accessed_distractors)
            }
        )
