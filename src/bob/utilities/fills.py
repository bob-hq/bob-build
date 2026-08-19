from string import Template as StringTemplate


class Template(StringTemplate):
    def get_identifiers(self) -> list[str]:
        # Extract all valid named or braced matches from the pattern
        ids = []
        for mo in self.pattern.finditer(self.template):
            named = mo.group("named") or mo.group("braced")
            if named and named not in ids:
                ids.append(named)
        return ids

    def is_valid(self) -> bool:
        # Check if the 'invalid' group matches anywhere in the template
        for mo in self.pattern.finditer(self.template):
            if mo.group("invalid"):
                return False
        return True
