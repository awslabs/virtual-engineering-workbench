import yaml


def get_path_list_with_roles(path: str) -> dict:
    parsed_file = parse_yaml_to_dict(path)
    return parsed_file


def parse_yaml_to_dict(path: str) -> dict:
    parsed_file = yaml.safe_load(open(path))
    formated_response = {}
    for path in parsed_file["paths"]:
        if "/internal" not in path:
            formated_response[path] = {}
            for method in parsed_file["paths"][path]:
                if method != "options":
                    method_normalized = method.upper()
                    formated_response[path][method_normalized] = []
                    for role in parsed_file["paths"][path][method]["tags"]:
                        formated_response[path][method_normalized].append(role.upper())

    return formated_response
