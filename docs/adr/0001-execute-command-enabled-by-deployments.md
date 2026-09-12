# Execute Command stays disabled in the image; deployments enable it

n8n 2.x excludes the Execute Command node by default via `NODES_EXCLUDE`. The custom image exists so workflows can run yt-dlp through that node, but it keeps n8n's default anyway; each deployment enables the node in its own Compose file, e.g. `NODES_EXCLUDE='["n8n-nodes-base.localFileTrigger"]'`. The custom image must stay universal and must not silently loosen n8n's security default for everyone who pulls it, so enabling shell access is a deployment setting.

## Considered Options

- **Bake `NODES_EXCLUDE` into the image.** yt-dlp would work with zero configuration, but n8n's security posture would change for every deployment and the image would no longer leave n8n's behaviour unchanged.

## Consequences

- The README must show the exact `NODES_EXCLUDE` value. n8n parses invalid JSON there as an empty list, which enables every node.
