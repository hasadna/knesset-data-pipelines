#!/usr/bin/env python
import yaml, sys

# updates the image url in the k8s deployment yaml files
# used by travis_deploy_script.sh

if len(sys.argv) != 3:
    print("usage: bin/k8s_update_deployment_image.py <k8s_deployment_name> <image_url>")
    exit(1)
else:
    deployment = sys.argv[1]
    image = sys.argv[2]

    if deployment not in ["app", "nginx"]:
        raise Exception("Unsupported deployment: {}".format(deployment))

    with open("devops/k8s/{}.yaml".format(deployment)) as f:
        docs = list(yaml.load_all(f))

    docs[0]["spec"]["template"]["spec"]["containers"][0]["image"] = image

    with open("devops/k8s/{}.yaml".format(deployment), "w") as f:
        yaml.dump_all(docs, f)

    exit(0)
