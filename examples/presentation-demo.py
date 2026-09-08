import json
from dropbrief.archdiff import compute_arch_delta
before={'model_type':'demo','hidden_size':128,'num_hidden_layers':4,'_name_or_path':'old'}
after={'model_type':'demo','hidden_size':256,'num_hidden_layers':4,'_name_or_path':'new'}
delta=compute_arch_delta(after,before,'demo-v2','demo-v1')
print(json.dumps({'identical_compared_fields':delta.is_identical_arch,'unchanged_fields':delta.unchanged_count,'changes':[x.model_dump() for x in delta.changed_fields]},indent=2))
