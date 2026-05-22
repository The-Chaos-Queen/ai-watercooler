import torch
data = torch.load("activation_sessions_1.5b/target_cheese_1_the_terminal_and_the_phoenix.pt", map_location="cpu", weights_only=False)
print(data[12].keys() if isinstance(data[12], dict) else type(data[12]))