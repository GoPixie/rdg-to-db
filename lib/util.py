def json_comment_filter(o):
    for k in list(o.keys()):
        if k == '//':
            del o[k]
        elif isinstance(o[k], dict):
            o[k] = json_comment_filter(o[k])
    return o
