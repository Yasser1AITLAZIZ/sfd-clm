"""
Script complet pour exécuter tous les steps du pipeline de bout en bout
et enregistrer les outputs de chaque étape
"""
import sys
import json
import logging
import asyncio
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend-mcp"))
sys.path.insert(0, str(project_root / "mock-salesforce"))

# Configuration
OUTPUT_DIR = Path(__file__).parent
TEST_RECORD_ID = "001XX000001"

# Setup logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = OUTPUT_DIR / f"complete_pipeline_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [COMPLETE] - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PipelineRunner:
    """Runner pour exécuter tous les steps du pipeline"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
        self.timestamp = timestamp
        
    def load_and_run_step(self, step_number: int, script_name: str, is_async: bool = False) -> Optional[Dict[str, Any]]:
        """Charge et exécute un script de step"""
        logger.info("=" * 80)
        logger.info(f"STEP {step_number}: {script_name}")
        logger.info("=" * 80)
        
        script_path = project_root / "debug-scripts" / script_name
        
        if not script_path.exists():
            logger.error(f"❌ Script not found: {script_path}")
            return None
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(f"step{step_number}", script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Execute the main function
            result = None
            if is_async:
                if hasattr(module, 'main'):
                    try:
                        result = asyncio.run(module.main())
                        logger.info(f"✅ Step {step_number} executed successfully")
                    except Exception as e:
                        logger.warning(f"⚠️  Step {step_number} execution had issues: {e}")
                else:
                    logger.warning(f"⚠️  No async main() function found in {script_name}")
            else:
                if hasattr(module, 'main'):
                    try:
                        result = module.main()
                        logger.info(f"✅ Step {step_number} executed successfully")
                    except Exception as e:
                        logger.warning(f"⚠️  Step {step_number} execution had issues: {e}")
                else:
                    logger.warning(f"⚠️  No main() function found in {script_name}")
            
            # Load the output JSON file if it exists (this is the primary source of data)
            output_json = project_root / "debug-scripts" / f"step{step_number}_output.json"
            step_data = {}
            
            if output_json.exists():
                try:
                    with open(output_json, 'r', encoding='utf-8') as f:
                        step_data = json.load(f)
                    logger.info(f"✅ Loaded output from {output_json.name}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not load output JSON: {e}")
            else:
                logger.warning(f"⚠️  Output JSON not found: {output_json.name}")
            
            # Also try to load conversion output if exists (for step 2, 6, 7)
            conversion_json = project_root / "debug-scripts" / f"step{step_number}_conversion_output.json"
            if conversion_json.exists():
                try:
                    with open(conversion_json, 'r', encoding='utf-8') as f:
                        step_data["conversion_output"] = json.load(f)
                    logger.info(f"✅ Loaded conversion output from {conversion_json.name}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not load conversion JSON: {e}")
            
            # Determine status based on whether we have data
            status = "success" if step_data else "warning"
            if result is None and not step_data:
                status = "error"
            
            # Save step output to complete pipeline directory
            step_output_file = self.output_dir / f"step{step_number}_output.json"
            with open(step_output_file, 'w', encoding='utf-8') as f:
                json.dump(step_data, f, indent=2, default=str, ensure_ascii=False)
            logger.info(f"✅ Step {step_number} output saved to: {step_output_file.name}")
            
            return {
                "step_number": step_number,
                "script_name": script_name,
                "status": status,
                "output": step_data,
                "result": str(result) if result is not None else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing step {step_number}: {type(e).__name__}: {e}", exc_info=True)
            return {
                "step_number": step_number,
                "script_name": script_name,
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def run_all_steps(self):
        """Exécute tous les steps du pipeline"""
        logger.info("=" * 80)
        logger.info("COMPLETE PIPELINE EXECUTION")
        logger.info("=" * 80)
        logger.info(f"Test Record ID: {TEST_RECORD_ID}")
        logger.info(f"Output Directory: {self.output_dir}")
        logger.info("")
        
        # Step 1: Mock Salesforce Retrieval
        logger.info("\n" + "=" * 80)
        step1_result = self.load_and_run_step(1, "step1_test_mock_salesforce_retrieval.py", is_async=False)
        self.results["step1"] = step1_result
        
        if not step1_result or step1_result.get("status") == "error":
            logger.error("❌ Step 1 failed. Cannot continue.")
            return
        
        # Step 2: Salesforce Client Fetch
        logger.info("\n" + "=" * 80)
        step2_result = self.load_and_run_step(2, "step2_test_salesforce_client_fetch.py", is_async=True)
        self.results["step2"] = step2_result
        
        if not step2_result or step2_result.get("status") == "error":
            logger.warning("⚠️  Step 2 failed or skipped. Continuing...")
        
        # Step 3: Preprocessing Pipeline
        logger.info("\n" + "=" * 80)
        step3_result = self.load_and_run_step(3, "step3_test_preprocessing_pipeline.py", is_async=True)
        self.results["step3"] = step3_result
        
        if not step3_result or step3_result.get("status") == "error":
            logger.warning("⚠️  Step 3 failed or skipped. Continuing...")
        
        # Step 4: Prompt Building
        logger.info("\n" + "=" * 80)
        step4_result = self.load_and_run_step(4, "step4_test_prompt_building.py", is_async=True)
        self.results["step4"] = step4_result
        
        if not step4_result or step4_result.get("status") == "error":
            logger.warning("⚠️  Step 4 failed or skipped. Continuing...")
        
        # Step 5: Prompt Optimization
        logger.info("\n" + "=" * 80)
        step5_result = self.load_and_run_step(5, "step5_test_prompt_optimization.py", is_async=True)
        self.results["step5"] = step5_result
        
        if not step5_result or step5_result.get("status") == "error":
            logger.warning("⚠️  Step 5 failed or skipped. Continuing...")
        
        # Step 6: MCP Formatting
        logger.info("\n" + "=" * 80)
        step6_result = self.load_and_run_step(6, "step6_test_mcp_formatting.py", is_async=True)
        self.results["step6"] = step6_result
        
        if not step6_result or step6_result.get("status") == "error":
            logger.warning("⚠️  Step 6 failed or skipped. Continuing...")
        
        # Step 7: MCP Sending
        logger.info("\n" + "=" * 80)
        step7_result = self.load_and_run_step(7, "step7_test_mcp_sending.py", is_async=True)
        self.results["step7"] = step7_result
        
        # Generate final summary
        self.generate_summary()
    
    def generate_summary(self):
        """Génère un résumé final de l'exécution"""
        logger.info("\n" + "=" * 80)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 80)
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "test_record_id": TEST_RECORD_ID,
            "steps": {},
            "overall_status": "success",
            "steps_completed": 0,
            "steps_failed": 0,
            "steps_warning": 0
        }
        
        for step_key, step_result in self.results.items():
            if step_result:
                step_num = step_result.get("step_number", 0)
                status = step_result.get("status", "unknown")
                summary["steps"][step_key] = {
                    "step_number": step_num,
                    "status": status,
                    "script_name": step_result.get("script_name", "unknown")
                }
                
                if status == "success":
                    summary["steps_completed"] += 1
                elif status == "error":
                    summary["steps_failed"] += 1
                    summary["overall_status"] = "failed"
                elif status == "warning":
                    summary["steps_warning"] += 1
                
                # Extract key metrics from output
                output = step_result.get("output", {})
                if output:
                    if step_key == "step1":
                        summary["steps"][step_key]["documents_count"] = len(output.get("documents", []))
                        summary["steps"][step_key]["fields_count"] = len(output.get("fields", []))
                    elif step_key == "step2":
                        summary["steps"][step_key]["fields_to_fill_count"] = len(output.get("fields_to_fill", []))
                    elif step_key == "step3":
                        summary["steps"][step_key]["documents_processed"] = len(output.get("documents", []))
                        summary["steps"][step_key]["fields_dictionary_count"] = len(output.get("fields_dictionary", {}))
                    elif step_key == "step4":
                        summary["steps"][step_key]["prompt_length"] = len(output.get("prompt", ""))
                    elif step_key == "step5":
                        summary["steps"][step_key]["original_length"] = output.get("original_length", 0)
                        summary["steps"][step_key]["optimized_length"] = output.get("optimized_length", 0)
                        summary["steps"][step_key]["quality_score"] = output.get("quality_score", 0)
                    elif step_key == "step6":
                        summary["steps"][step_key]["message_id"] = output.get("message_id", "N/A")
                        summary["steps"][step_key]["context_documents_count"] = len(output.get("context", {}).get("documents", []))
                        summary["steps"][step_key]["context_fields_count"] = len(output.get("context", {}).get("fields", []))
                    elif step_key == "step7":
                        extracted_data = output.get("extracted_data", {})
                        summary["steps"][step_key]["extracted_data_count"] = len(extracted_data) if extracted_data else 0
                        summary["steps"][step_key]["confidence_scores_count"] = len(output.get("confidence_scores", {}))
                        summary["steps"][step_key]["status"] = output.get("status", "unknown")
                        summary["steps"][step_key]["quality_score"] = output.get("quality_score")
        
        # Save summary
        summary_file = self.output_dir / f"pipeline_summary_{self.timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"✅ Summary saved to: {summary_file.name}")
        
        # Print summary
        logger.info(f"\nOverall Status: {summary['overall_status'].upper()}")
        logger.info(f"Steps Completed: {summary['steps_completed']}/7")
        logger.info(f"Steps Failed: {summary['steps_failed']}/7")
        logger.info(f"Steps Warning: {summary['steps_warning']}/7")
        
        logger.info("\nStep Details:")
        for step_key, step_info in summary["steps"].items():
            status_icon = "✅" if step_info["status"] == "success" else "❌" if step_info["status"] == "error" else "⚠️"
            logger.info(f"  {status_icon} {step_key.upper()}: {step_info['status']}")
            
            # Show key metrics
            if "documents_count" in step_info:
                logger.info(f"     - Documents: {step_info['documents_count']}")
            if "fields_count" in step_info:
                logger.info(f"     - Fields: {step_info['fields_count']}")
            if "extracted_data_count" in step_info:
                logger.info(f"     - Extracted Data: {step_info['extracted_data_count']} fields")
                if "quality_score" in step_info and step_info["quality_score"]:
                    logger.info(f"     - Quality Score: {step_info['quality_score']:.2%}")
        
        # Save complete results
        complete_results_file = self.output_dir / f"complete_results_{self.timestamp}.json"
        with open(complete_results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": summary,
                "detailed_results": self.results
            }, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Complete results saved to: {complete_results_file.name}")
        
        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE EXECUTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📁 All outputs saved in: {self.output_dir}")
        logger.info(f"📄 Log file: {log_file.name}")


async def main():
    """Main function"""
    runner = PipelineRunner(OUTPUT_DIR)
    await runner.run_all_steps()


if __name__ == "__main__":
    asyncio.run(main())

