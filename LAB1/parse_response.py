def parse_response(response_data):
    try:
        header_end = response_data.find(b'\r\n\r\n')
        if header_end == -1:
            raise ValueError("Invalid HTTP response: No header-body separator found.")
        
        header_section = response_data[:header_end].decode('utf-8')
        body = response_data[header_end + 4:]

        lines = header_section.split('\r\n')
        status_line = lines[0]
        parts = status_line.split(' ', 2)
        status_code = int(parts[1])

        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        return status_code, headers, body
    except Exception as e:
        raise ValueError(f"Failed to parse HTTP response: {e}")
    