import os, sys

class Algorithms:
    def resourcePath(relative_path):
        # Get the absolute path of the script
        script_path = os.path.abspath(sys.argv[0])

        # Use the script's directory as the base path for other filepaths
        base_path = os.path.dirname(script_path)


        return os.path.join(base_path, relative_path)
    
    def levenshtein_distance(s1, s2):
        if len(s1) < len(s2):
            return Algorithms.levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]