"""Test individual workflow components with fake data"""
import asyncio
from typing import Dict, Any

# Import services
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Note: These imports assume the backend-mcp directory is in the Python path
# For testing, you may need to adjust the import paths based on your setup

try:
    from app.services.preprocessing.document_preprocessor import DocumentPreprocessor
    from app.services.preprocessing.fields_preprocessor import FieldsDictionaryPreprocessor
    from app.services.preprocessing.preprocessing_pipeline import PreprocessingPipeline
    from app.services.prompting.prompt_builder import PromptBuilder
    from app.services.prompting.prompt_optimizer import PromptOptimizer
    from app.services.mcp.mcp_message_formatter import MCPMessageFormatter
    from app.models.schemas import (
        DocumentResponseSchema,
        FieldToFillResponseSchema,
        SalesforceDataResponseSchema
    )
except ImportError:
    # Fallback for different import structure
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend-mcp"))
    from app.services.preprocessing.document_preprocessor import DocumentPreprocessor
    from app.services.preprocessing.fields_preprocessor import FieldsDictionaryPreprocessor
    from app.services.preprocessing.preprocessing_pipeline import PreprocessingPipeline
    from app.services.prompting.prompt_builder import PromptBuilder
    from app.services.prompting.prompt_optimizer import PromptOptimizer
    from app.services.mcp.mcp_message_formatter import MCPMessageFormatter
    from app.models.schemas import (
        DocumentResponseSchema,
        FieldToFillResponseSchema,
        SalesforceDataResponseSchema
    )


def create_fake_salesforce_data() -> SalesforceDataResponseSchema:
    """Create fake Salesforce data for testing"""
    documents = [
        DocumentResponseSchema(
            document_id="doc_1",
            name="facture.pdf",
            url="https://example.com/facture.pdf",
            type="application/pdf",
            indexed=True
        ),
        DocumentResponseSchema(
            document_id="doc_2",
            name="justificatif.jpg",
            url="https://example.com/justificatif.jpg",
            type="image/jpeg",
            indexed=True
        )
    ]
    
    fields = [
        FieldToFillResponseSchema(
            field_name="montant_total",
            field_type="currency",
            value=None,
            required=True,
            label="Montant total"
        ),
        FieldToFillResponseSchema(
            field_name="date_facture",
            field_type="date",
            value=None,
            required=True,
            label="Date de facture"
        ),
        FieldToFillResponseSchema(
            field_name="beneficiaire_nom",
            field_type="text",
            value=None,
            required=True,
            label="Nom du bénéficiaire"
        ),
        FieldToFillResponseSchema(
            field_name="numero_facture",
            field_type="text",
            value="FAC-2024-001",
            required=True,
            label="Numéro de facture"
        )
    ]
    
    return SalesforceDataResponseSchema(
        record_id="001XXXX",
        record_type="Claim",
        documents=documents,
        fields_to_fill=fields
    )


async def test_document_preprocessor():
    """Test document preprocessor"""
    print("=" * 80)
    print("Testing Document Preprocessor")
    print("=" * 80)
    
    preprocessor = DocumentPreprocessor()
    fake_data = create_fake_salesforce_data()
    
    processed_docs = await preprocessor.process_documents(fake_data.documents)
    
    print(f"✅ Processed {len(processed_docs)} documents")
    for doc in processed_docs:
        print(f"   - {doc.name}: Quality score = {doc.quality_score}")
    
    return processed_docs


async def test_fields_preprocessor():
    """Test fields preprocessor"""
    print("\n" + "=" * 80)
    print("Testing Fields Preprocessor")
    print("=" * 80)
    
    preprocessor = FieldsDictionaryPreprocessor()
    fake_data = create_fake_salesforce_data()
    
    fields_dict = await preprocessor.prepare_fields_dictionary(
        fake_data.fields_to_fill,
        fake_data.record_type
    )
    
    print(f"✅ Processed {len(fields_dict.fields)} fields")
    print(f"   - Empty fields: {len(fields_dict.empty_fields)}")
    print(f"   - Prefilled fields: {len(fields_dict.prefilled_fields)}")
    print(f"   - Prioritized fields: {len(fields_dict.prioritized_fields)}")
    
    return fields_dict


async def test_preprocessing_pipeline():
    """Test preprocessing pipeline"""
    print("\n" + "=" * 80)
    print("Testing Preprocessing Pipeline")
    print("=" * 80)
    
    pipeline = PreprocessingPipeline()
    fake_data = create_fake_salesforce_data()
    
    preprocessed = await pipeline.execute_preprocessing(fake_data)
    
    print(f"✅ Preprocessing completed")
    print(f"   - Record ID: {preprocessed.record_id}")
    print(f"   - Documents: {len(preprocessed.processed_documents)}")
    print(f"   - Fields: {len(preprocessed.fields_dictionary.fields)}")
    print(f"   - Processing time: {preprocessed.metrics.get('processing_time_seconds', 0):.2f}s")
    
    return preprocessed


async def test_prompt_builder():
    """Test prompt builder"""
    print("\n" + "=" * 80)
    print("Testing Prompt Builder")
    print("=" * 80)
    
    builder = PromptBuilder()
    fake_data = create_fake_salesforce_data()
    
    # Create preprocessed data (simplified)
    from app.services.preprocessing.preprocessing_pipeline import PreprocessingPipeline
    pipeline = PreprocessingPipeline()
    preprocessed = await pipeline.execute_preprocessing(fake_data)
    
    prompt_response = await builder.build_initialization_prompt(
        preprocessed,
        "Remplis tous les champs manquants"
    )
    
    print(f"✅ Prompt built")
    print(f"   - Scenario: {prompt_response.scenario_type}")
    print(f"   - Prompt length: {len(prompt_response.prompt)} characters")
    print(f"   - Estimated tokens: {prompt_response.metadata.get('estimated_tokens', 0)}")
    print(f"\n   Prompt preview (first 200 chars):")
    print(f"   {prompt_response.prompt[:200]}...")
    
    return prompt_response


async def test_prompt_optimizer():
    """Test prompt optimizer"""
    print("\n" + "=" * 80)
    print("Testing Prompt Optimizer")
    print("=" * 80)
    
    optimizer = PromptOptimizer()
    builder = PromptBuilder()
    
    fake_data = create_fake_salesforce_data()
    pipeline = PreprocessingPipeline()
    preprocessed = await pipeline.execute_preprocessing(fake_data)
    
    prompt_response = await builder.build_initialization_prompt(
        preprocessed,
        "Remplis tous les champs manquants"
    )
    
    optimized = await optimizer.optimize(prompt_response, max_tokens=1000)
    
    print(f"✅ Prompt optimized")
    print(f"   - Original length: {optimized.original_length}")
    print(f"   - Optimized length: {optimized.optimized_length}")
    print(f"   - Tokens estimated: {optimized.tokens_estimated}")
    print(f"   - Quality score: {optimized.quality_score}")
    print(f"   - Optimizations applied: {optimized.optimizations_applied}")
    
    return optimized


async def test_mcp_formatter():
    """Test MCP message formatter"""
    print("\n" + "=" * 80)
    print("Testing MCP Message Formatter")
    print("=" * 80)
    
    formatter = MCPMessageFormatter()
    
    # Create fake prompt
    prompt = "Extract data from documents..."
    
    context = {
        "documents": [
            {
                "document_id": "doc_1",
                "name": "facture.pdf",
                "type": "application/pdf"
            }
        ],
        "fields": [
            {
                "field_name": "montant_total",
                "field_type": "currency"
            }
        ],
        "session_id": "test_session_123"
    }
    
    metadata = {
        "record_id": "001XXXX",
        "record_type": "Claim",
        "timestamp": "2024-01-15T10:00:00Z"
    }
    
    mcp_message = formatter.format_message(prompt, context, metadata)
    
    print(f"✅ MCP message formatted")
    print(f"   - Message ID: {mcp_message.message_id}")
    print(f"   - Prompt length: {len(mcp_message.prompt)}")
    print(f"   - Documents in context: {len(mcp_message.context.get('documents', []))}")
    print(f"   - Record ID: {mcp_message.metadata.record_id}")
    
    return mcp_message


async def run_all_component_tests():
    """Run all component tests"""
    print("\n" + "=" * 80)
    print("OPTICLAIMS COMPONENT TESTS")
    print("=" * 80)
    print()
    
    try:
        await test_document_preprocessor()
        await test_fields_preprocessor()
        await test_preprocessing_pipeline()
        await test_prompt_builder()
        await test_prompt_optimizer()
        await test_mcp_formatter()
        
        print("\n" + "=" * 80)
        print("✅ All component tests completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_component_tests())

