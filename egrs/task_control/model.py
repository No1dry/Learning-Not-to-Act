"""Small task context and zero-output residual; no policy or data metadata."""
import torch
from torch import nn


class TaskControlModules(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        if type(hidden_dim) is not int or hidden_dim < 1:
            raise ValueError('hidden_dim must be a positive integer')
        self.hidden_dim = hidden_dim
        self.enabled = True
        self.context = nn.Sequential(nn.Linear(2 * hidden_dim, 256), nn.SiLU(), nn.Linear(256, 128))
        self.norm = nn.LayerNorm(hidden_dim)
        self.W_h = nn.Linear(hidden_dim, 256, bias=False)
        self.W_z = nn.Linear(128, 256, bias=False)
        self.W_p = nn.Linear(8, 256, bias=False)
        self.W_out = nn.Linear(256, hidden_dim, bias=False)
        self.count_head = nn.Linear(128, 3)
        nn.init.zeros_(self.W_out.weight)

    def encode_context(self, visual, instruction):
        return self.context(torch.cat((visual.float().mean(1), instruction.float().mean(1)), dim=-1))

    def forward(self, h, z, proprio):
        if not self.enabled:
            return h
        value = self.W_h(self.norm(h.float())) + self.W_z(z.float()).unsqueeze(1)
        value = value + self.W_p(proprio.float()).unsqueeze(1)
        return h + self.W_out(torch.nn.functional.silu(value)).to(h.dtype)
