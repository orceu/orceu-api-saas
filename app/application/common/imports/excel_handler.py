import os
import pandas as pd


class ExcelHandler:
    allowed_extensions = ['.xls', '.xlsx', '.csv']

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.extension = os.path.splitext(file_path)[1].lower()
        self._validate_extension()

    def _validate_extension(self):
        if self.extension not in self.allowed_extensions:
            raise ValueError(f"Extensão de arquivo não suportada: {self.extension}")

    def read(self, **kwargs):
        """Lê o Excel ou CSV e retorna um DataFrame pandas."""
        if self.extension == '.csv':
            return pd.read_csv(self.file_path, **kwargs)
        elif self.extension in ['.xls', '.xlsx']:
            return pd.read_excel(self.file_path, **kwargs)
        else:
            raise ValueError(f"Extensão de arquivo não suportada: {self.extension}")

    def to_list(self):
        """Retorna os dados do arquivo em lista de dicionários (para debug)."""
        df = self.read()
        return df.to_dict(orient="records")
