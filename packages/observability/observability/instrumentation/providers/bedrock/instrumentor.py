from __future__ import annotations

import importlib
import logging
import time
import json
import io
from typing import Any, Dict, Optional, Tuple

from opentelemetry.trace import StatusCode

from observability.instrumentation.core.base_instrumentor import BaseInstrumentor
from observability.instrumentation.core.operations import OperationSpec
from observability.instrumentation.common.span_management import start_span, end_span, set_attributes
from observability.instrumentation.providers.bedrock.adapter import BedrockAdapter
from observability.instrumentation.core.wrapper_factory import _record_agent_run, _record_metrics

logger = logging.getLogger(__name__)

class BedrockInstrumentor(BaseInstrumentor):
    def __init__(self) -> None:
        super().__init__()
        self._original_make_api_call = None

    @property
    def target_packages(self) -> tuple[str, ...]:
        return ("boto3",)

    def _do_instrument(self, module: Any) -> None:
        try:
            import botocore.client
        except ImportError:
            logger.warning("botocore not found, cannot instrument Bedrock")
            return

        self._original_make_api_call = botocore.client.BaseClient._make_api_call
        
        def wrapper(client_instance, operation_name, api_params):
            return self._make_api_call_wrapper(client_instance, operation_name, api_params)
            
        botocore.client.BaseClient._make_api_call = wrapper

    def _do_uninstrument(self) -> None:
        if self._original_make_api_call:
            import botocore.client
            botocore.client.BaseClient._make_api_call = self._original_make_api_call
            self._original_make_api_call = None

    def _make_api_call_wrapper(self, client_instance, operation_name, api_params):
        # Check if this is Bedrock Runtime
        # client_instance.meta.service_model.service_id should be 'Bedrock Runtime'
        try:
            service_name = client_instance.meta.service_model.service_id
        except AttributeError:
            service_name = ""

        if service_name != 'Bedrock Runtime':
            return self._original_make_api_call(client_instance, operation_name, api_params)

        # It is Bedrock. Check operation.
        op_spec = None
        if operation_name == 'InvokeModel':
            op_spec = OperationSpec(
                name="invoke_model",
                method_name="invoke_model",
                span_name="bedrock.invoke_model",
                kind="generate",
                streaming=False,
                asynchronous=False
            )
        # TODO: Handle InvokeModelWithResponseStream
        
        if not op_spec or not self._config or not self._config.instrument_llm_calls:
            return self._original_make_api_call(client_instance, operation_name, api_params)

        # Instrumentation logic
        adapter = BedrockAdapter()
        start_ns = time.perf_counter_ns()
        truncate_limit = int(self._config.privacy_truncate_chars) if self._config.privacy_truncate_chars else 2000
        
        # Parse request
        # args for parse_request: (client_instance, operation_name, api_params)
        try:
            request = adapter.parse_request(op_spec, (client_instance, operation_name, api_params), {}, truncate_limit)
            request_attrs = adapter.build_request_attributes(op_spec, request)
            span_ctx, span = start_span(op_spec.span_name, request_attrs)
        except Exception as e:
            logger.warning(f"Failed to start span for Bedrock: {e}")
            return self._original_make_api_call(client_instance, operation_name, api_params)
        
        success = False
        response_model = None
        result = None
        
        try:
            # Call original
            result = self._original_make_api_call(client_instance, operation_name, api_params)
            
            # Handle body
            if isinstance(result, dict) and 'body' in result:
                from botocore.response import StreamingBody
                
                body_stream = result['body']
                # Only read if it is a StreamingBody
                if isinstance(body_stream, StreamingBody):
                    body_bytes = body_stream.read()
                    
                    # Restore the stream for the user
                    new_stream = io.BytesIO(body_bytes)
                    result['body'] = StreamingBody(new_stream, len(body_bytes))
                    
                    # Parse the body
                    try:
                        parsed_body = json.loads(body_bytes)
                        result['_astra_response_body'] = parsed_body
                    except:
                        pass
            
            # Parse response
            response_model = adapter.parse_response(op_spec, result, truncate_limit)
            response_attrs = adapter.build_response_attributes(op_spec, response_model)
            usage_attrs = adapter.build_usage_attributes(op_spec, response_model.usage)
            cost_attrs = adapter.calculate_cost(op_spec, request, response_model)
            
            set_attributes(span, response_attrs)
            set_attributes(span, usage_attrs)
            if cost_attrs:
                set_attributes(span, cost_attrs)
                
            _record_agent_run(span, adapter, op_spec, request, response_model, cost_attrs, start_ns)
            end_span(span_ctx, span, status_code=StatusCode.OK)
            success = True
            return result

        except Exception as e:
            end_span(span_ctx, span, status_code=StatusCode.ERROR, error=e)
            raise
        finally:
             _record_metrics(
                operation=op_spec,
                start_ns=start_ns,
                success=success,
                usage=response_model.usage if response_model is not None else None,
            )
