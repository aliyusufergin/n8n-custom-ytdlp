"""Publish tested OCI archives and an unchanged runners index; record verified results."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


CUSTOM = "docker.io/aliyusufergin/n8n-ytdlp"
RUNNERS = "docker.io/aliyusufergin/n8n-ytdlp-runners"
OCI_INDEX = "application/vnd.oci.image.index.v1+json"


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def archive_index(archive: tarfile.TarFile) -> tuple[dict, dict]:
    stream = archive.extractfile("index.json")
    if stream is None:
        raise ValueError("OCI archive has no index")
    layout = json.load(stream)
    if len(layout["manifests"]) != 1:
        raise ValueError("expected one build result in the OCI archive")
    descriptor = layout["manifests"][0]
    index = archive_blob(archive, descriptor)
    if index["mediaType"] != OCI_INDEX:
        raise ValueError("build result must be an OCI index")
    return descriptor, index


def archive_blob(archive: tarfile.TarFile, descriptor: dict) -> dict:
    algorithm, value = descriptor["digest"].split(":")
    if algorithm != "sha256":
        raise ValueError("expected a sha256 digest")
    stream = archive.extractfile(f"blobs/sha256/{value}")
    if stream is None:
        raise ValueError("missing OCI blob")
    data = stream.read()
    if digest(data) != descriptor["digest"] or len(data) != descriptor["size"]:
        raise ValueError("OCI blob does not match its descriptor")
    return json.loads(data)


def inspect_archive(path: Path, arch: str, build_tag: str) -> dict:
    """Check the runnable manifest, its label, and both bound BuildKit attestations."""
    with tarfile.open(path) as archive:
        descriptor, index = archive_index(archive)
        images = [entry for entry in index["manifests"]
                  if entry.get("platform", {}).get("os") == "linux"
                  and entry["platform"].get("architecture") == arch]
        if len(images) != 1 or len(index["manifests"]) != 2:
            raise ValueError("expected one native image and one attestation manifest")
        image = images[0]
        manifest = archive_blob(archive, image)
        config = archive_blob(archive, manifest["config"])
        if config["architecture"] != arch or config["os"] != "linux":
            raise ValueError("unexpected image platform")
        if config["config"]["Labels"]["io.github.aliyusufergin.n8n-ytdlp.build-tag"] != build_tag:
            raise ValueError("image label differs from the plan's build tag")
        attestation = next(entry for entry in index["manifests"] if entry != image)
        if attestation.get("annotations", {}).get("vnd.docker.reference.digest") != image["digest"]:
            raise ValueError("attestation does not reference the tested image")
        predicates = set()
        for layer in archive_blob(archive, attestation)["layers"]:
            statement = archive_blob(archive, layer)
            if not any(subject.get("digest", {}).get("sha256") == image["digest"].split(":")[1]
                       for subject in statement.get("subject", [])):
                raise ValueError("attestation subject differs from the tested image")
            predicates.add(statement["predicateType"])
        if not any(value.startswith("https://slsa.dev/provenance/") for value in predicates):
            raise ValueError("BuildKit provenance missing")
        if "https://spdx.dev/Document" not in predicates:
            raise ValueError("BuildKit SBOM missing")
        return {"arch": arch, "build_tag": build_tag, "index_digest": descriptor["digest"],
                "image_digest": image["digest"], "manifests": index["manifests"]}


def regctl(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.check_output(["regctl", *args], input=data)


def verify_remote(reference: str, expected: str) -> None:
    raw = regctl("manifest", "get", reference, "--format", "raw-body")
    if digest(raw) != expected:
        raise ValueError(f"published manifest differs from expected digest: {reference}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if plan["build"] is not True:
        parser.error("plan does not request a build")
    # Validate both artifacts and successful-test receipts before any registry write.
    manifests = []
    archives = []
    for arch in ("amd64", "arm64"):
        path = args.artifacts / f"candidate-{arch}" / "image.tar"
        evidence = inspect_archive(path, arch, plan["build_tag"])
        if evidence != json.loads(path.with_suffix(".json").read_text()):
            raise ValueError(f"{arch} archive differs from the successful test receipt")
        manifests.extend(evidence["manifests"])
        archives.append((path, evidence))
    index = json.dumps({"schemaVersion": 2, "mediaType": OCI_INDEX,
                        "manifests": manifests}, separators=(",", ":")).encode()
    index_digest = digest(index)
    for path, evidence in archives:
        target = f'{CUSTOM}@{evidence["index_digest"]}'
        regctl("image", "import", target, str(path))
        verify_remote(target, evidence["index_digest"])
        for manifest in evidence["manifests"]:
            verify_remote(f'{CUSTOM}@{manifest["digest"]}', manifest["digest"])
    # Upload by digest first. Floating tags move only after both payloads exist.
    regctl("manifest", "put", f"{CUSTOM}@{index_digest}", "--content-type", OCI_INDEX, data=index)
    verify_remote(f"{CUSTOM}@{index_digest}", index_digest)
    runners_digest = plan["new_lock"]["n8n"]["runners_digest"]
    regctl("image", "copy", f"docker.io/n8nio/runners@{runners_digest}",
           f"{RUNNERS}@{runners_digest}")
    verify_remote(f"{RUNNERS}@{runners_digest}", runners_digest)
    for tag in [plan["build_tag"], *plan["floating_tags"]]:
        for repository, expected in ((CUSTOM, index_digest), (RUNNERS, runners_digest)):
            regctl("image", "copy", f"{repository}@{expected}", f"{repository}:{tag}")
            verify_remote(f"{repository}:{tag}", expected)
    lock = plan["new_lock"]
    lock["published"] = {"build_tag": plan["build_tag"], "image_digest": index_digest}
    args.result.write_text(json.dumps(lock, indent=2) + "\n")
    print(f'Published {plan["build_tag"]}: {index_digest}')


if __name__ == "__main__":
    main()
