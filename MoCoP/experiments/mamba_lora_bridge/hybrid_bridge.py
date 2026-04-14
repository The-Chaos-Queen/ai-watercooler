import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, AutoConfig

class HybridBridge(nn.Module):
    """
    MVP-4 Hybrid Bridge Architecture.
    
    Instead of compressing the Mamba state sequence to a single vector, this bridge
    uses a small hybrid sequence model (e.g., a 0.5B parameter model with mixed 
    Attention and SSM layers) to map the Mamba state sequence directly into a 
    sequence of 'Virtual Tokens' (soft prompts) for the target Qwen model.
    """
    def __init__(
        self,
        hybrid_model_id: str = "Qwen/Qwen2.5-0.5B", # Base model to be hybridized
        mamba_hidden_dim: int = 2560,
        target_hidden_dim: int = 3584, # e.g., Qwen-7B hidden size
        num_virtual_tokens: int = 16,
    ):
        super().__init__()
        self.mamba_hidden_dim = mamba_hidden_dim
        self.target_hidden_dim = target_hidden_dim
        self.num_virtual_tokens = num_virtual_tokens
        
        # 1. Input Projection: Map Mamba dims to the small Hybrid model's dims
        hybrid_config = AutoConfig.from_pretrained(hybrid_model_id)
        self.hybrid_dim = hybrid_config.hidden_size
        self.input_proj = nn.Linear(mamba_hidden_dim, self.hybrid_dim)
        
        # 2. The Hybrid Core
        # In a full implementation, this would be a model loaded via the 
        # awslabs/hybrid-model-factory methodology (e.g. replacing some attn layers with Mamba2).
        # For this draft, we wrap a standard small model.
        self.hybrid_core = AutoModelForCausalLM.from_pretrained(hybrid_model_id)
        
        # 3. Output Projection & Shaping: Map back to target Qwen dims
        self.output_proj = nn.Linear(self.hybrid_dim, target_hidden_dim)
        
        # 4. Virtual Token Queries
        # These are learned embeddings that "query" the hybrid core to produce the final soft prompts
        self.virtual_queries = nn.Parameter(torch.randn(1, num_virtual_tokens, self.hybrid_dim))

    def forward(self, mamba_state_sequence: torch.Tensor) -> torch.Tensor:
        """
        Args:
            mamba_state_sequence: [batch_size, sequence_length, mamba_hidden_dim]
                The raw recurrent state sequence from Mamba.
        
        Returns:
            virtual_tokens: [batch_size, num_virtual_tokens, target_hidden_dim]
                The soft prompt sequence to be prepended to the target Qwen's inputs.
        """
        batch_size = mamba_state_sequence.size(0)
        
        # 1. Map Mamba states into the hybrid model's dimensional space
        # [batch, seq_len, hybrid_dim]
        projected_states = self.input_proj(mamba_state_sequence)
        
        # 2. Append the learned virtual queries to the end of the projected sequence
        # We want the hybrid core to attend to the Mamba context and output specific tokens
        # [batch, num_virtual_tokens, hybrid_dim]
        expanded_queries = self.virtual_queries.expand(batch_size, -1, -1)
        
        # Combine: [batch, seq_len + num_virtual_tokens, hybrid_dim]
        hybrid_input = torch.cat([projected_states, expanded_queries], dim=1)
        
        # 3. Pass through the hybrid core
        # We use the underlying model without the LM head to get raw hidden states
        # (Assuming standard HF model structure where .model or .transformer is the backbone)
        if hasattr(self.hybrid_core, "model"):
            hybrid_outputs = self.hybrid_core.model(inputs_embeds=hybrid_input)
        elif hasattr(self.hybrid_core, "transformer"):
             hybrid_outputs = self.hybrid_core.transformer(inputs_embeds=hybrid_input)
        else:
             raise NotImplementedError("Unrecognized backbone structure in hybrid core.")
             
        last_hidden_states = hybrid_outputs.last_hidden_state
        
        # 4. Extract only the representations corresponding to the virtual queries
        # [batch, num_virtual_tokens, hybrid_dim]
        query_outputs = last_hidden_states[:, -self.num_virtual_tokens:, :]
        
        # 5. Project to the target model's dimensionality
        # [batch, num_virtual_tokens, target_hidden_dim]
        virtual_tokens = self.output_proj(query_outputs)
        
        return virtual_tokens
