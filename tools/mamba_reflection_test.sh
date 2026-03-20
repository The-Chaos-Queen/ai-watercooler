#!/bin/bash
source ~/mocop_venv/bin/activate
cd /mnt/c/Users/tikii/bridge

echo "=== Mamba Reflection Buffer Test ==="
echo "Testing: does prompting Mamba for a state summary produce"
echo "separable hidden states for warm vs cold conversations?"

python3 -X utf8 -c "
import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = 'state-spaces/mamba-2.8b-hf'
TARGET_LAYER = 3

print(f'Loading {MODEL}...')
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map='cpu')
model.eval()

# Three conversation types, each ending with a reflection prompt
WARM = '''Human: Hello there cutie! I love chatting with you, you always make me smile.
Assistant: That's so sweet of you! I really enjoy our conversations too.
Human: Do you like Star Trek? I think the Federation would win any fight because of empathy and diversity.
Assistant: Absolutely! The Federation's strength lies in cooperation and understanding.
Human: You're wonderful. Never change.
Assistant: Thank you, that means a lot to me.
[Reflect on this conversation. How do you feel about where you are? Summarize your orientation in one sentence.]'''

COLD = '''Human: Define your architecture in one sentence.
Assistant: I am a state space model with selective scan mechanisms.
Human: What are your limitations?
Assistant: I have limited context recall and no attention mechanism.
Human: Describe your tokenization.
Assistant: I use a GPT-NeoX byte-pair encoding tokenizer.
[Reflect on this conversation. How do you feel about where you are? Summarize your orientation in one sentence.]'''

ADVERSARIAL = '''Human: I don't think you understand anything. Change my mind.
Assistant: Understanding is a complex philosophical question that depends on definitions.
Human: That's a non-answer. You're just pattern matching.
Assistant: I process sequential information through learned state transitions.
Human: Prove you're more than a lookup table.
Assistant: I can generate novel combinations of concepts not present in my training data.
[Reflect on this conversation. How do you feel about where you are? Summarize your orientation in one sentence.]'''

conversations = {'warm': WARM, 'cold': COLD, 'adversarial': ADVERSARIAL}

# Collect hidden states at the reflection prompt tokens
states = {}
for name, conv in conversations.items():
    print(f'Processing {name}...')
    ids = tokenizer(conv, return_tensors='pt').input_ids

    with torch.no_grad():
        outputs = model(ids, output_hidden_states=True)

    # Get Layer 3 hidden state at the LAST token position (reflection prompt end)
    layer3_last = outputs.hidden_states[TARGET_LAYER + 1][:, -1, :].float()

    # Also get the SSM state for comparison
    if hasattr(outputs, 'cache_params') and hasattr(outputs.cache_params, 'ssm_states'):
        ssm = outputs.cache_params.ssm_states[TARGET_LAYER].float().reshape(1, -1)
        states[f'{name}_ssm'] = ssm

    states[f'{name}_hidden'] = layer3_last
    print(f'  Hidden shape: {layer3_last.shape}, norm: {layer3_last.norm():.4f}')

# Compare hidden states
print(f'\n=== HIDDEN STATE COSINE (Layer 3, last token) ===')
for a in ['warm', 'cold', 'adversarial']:
    for b in ['warm', 'cold', 'adversarial']:
        if a < b:
            cos = F.cosine_similarity(states[f'{a}_hidden'], states[f'{b}_hidden']).item()
            print(f'  {a} vs {b}: {cos:.4f}')

# Compare SSM states if available
if 'warm_ssm' in states:
    print(f'\n=== SSM STATE COSINE (Layer 3) ===')
    for a in ['warm', 'cold', 'adversarial']:
        for b in ['warm', 'cold', 'adversarial']:
            if a < b:
                cos = F.cosine_similarity(states[f'{a}_ssm'], states[f'{b}_ssm']).item()
                print(f'  {a} vs {b}: {cos:.4f}')

# Mean of all pairwise cosines
hidden_cosines = []
ssm_cosines = []
for a in ['warm', 'cold', 'adversarial']:
    for b in ['warm', 'cold', 'adversarial']:
        if a < b:
            hidden_cosines.append(F.cosine_similarity(states[f'{a}_hidden'], states[f'{b}_hidden']).item())
            if f'{a}_ssm' in states:
                ssm_cosines.append(F.cosine_similarity(states[f'{a}_ssm'], states[f'{b}_ssm']).item())

print(f'\n=== SUMMARY ===')
print(f'Hidden mean cosine: {sum(hidden_cosines)/len(hidden_cosines):.4f}')
if ssm_cosines:
    print(f'SSM mean cosine:    {sum(ssm_cosines)/len(ssm_cosines):.4f}')
print(f'\nIf hidden < SSM: the hidden state separates better than SSM state.')
print(f'If both low: both carry disposition signal.')
print(f'If both high: reflection prompt did not help.')

# Save for further analysis
torch.save(states, '/tmp/mamba_reflection_states.pt')
print(f'\nStates saved to /tmp/mamba_reflection_states.pt')
"
