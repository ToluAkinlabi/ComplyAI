# ComplyAI
ComplyAI is an AI tool that does cyber security compliance and audit assessment. It compares a company’s current security policies against industry standard frameworks and it identifies the gaps and gives recommendations based on the gaps.

### Steps
#### Run the scripts/framework_loader.py to convert all framework pdf to json if not already done. Ensure to inlude the path and also place the pdf in the data/framework_raw folder.

#### When a new control is added, rebuild the cached index by running the script/rebuild_index.py before moving on.