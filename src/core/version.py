"""
# src/core/version.py
Gerenciador de versões para o projeto.
"""
import json
import os
from datetime import datetime

class VersionAnalyzer:
    """Analisador de versões do projeto."""
    
    def __init__(self):
        """Inicializa o analisador de versões."""
        self.version_file = '.version.json'
        self.load_version_data()
        
    def load_version_data(self) -> None:
        """Carrega dados de versão do arquivo."""
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                self.version_data = json.load(f)
        except FileNotFoundError:
            self.version_data = {
                "current": "0.1.0",
                "manifest": {
                    "include": [
                        "LICENSE",
                        "README.md",
                        "src/configs/*.yaml"
                    ]
                },
                "history": {
                    "0.1.0": {
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "commit": "initial",
                        "increment_type": "minor",
                        "previous_version": "0.0.0"
                    }
                }
            }
            self.save_version_data()
    
    def save_version_data(self) -> None:
        """Salva dados de versão no arquivo."""
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(self.version_data, f, indent=4)
            
    def get_current_version(self) -> str:
        """Retorna a versão atual."""
        return self.version_data['current']
    
    def increment_version(self, current: str, increment_type: str) -> str:
        """
        Incrementa a versão seguindo semver.
        
        Args:
            current: Versão atual
            increment_type: Tipo de incremento (major, minor, patch)
            
        Returns:
            str: Nova versão
        """
        major, minor, patch = map(int, current.split('.'))
        
        if increment_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif increment_type == 'minor':
            minor += 1
            patch = 0
        else:  # patch
            patch += 1
            
        return f"{major}.{minor}.{patch}"
    
    def smart_bump(self) -> None:
        """
        Incrementa a versão automaticamente baseado no último commit.
        """
        try:
            # Obter o último commit
            result = os.popen('git log -1 --pretty=%B').read().strip().lower()
            
            # Determina o tipo de incremento (sempre patch para simplificar)
            increment_type = 'patch'
            print(f"Incrementando versão como '{increment_type}'")
            
            # Incrementa a versão
            current = self.get_current_version()
            new_version = self.increment_version(current, increment_type)
            
            # Atualiza o histórico
            self.version_data['history'][new_version] = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "commit": result,
                "increment_type": increment_type,
                "previous_version": current
            }
            
            # Atualiza a versão atual
            self.version_data['current'] = new_version
            
            # Salva as alterações
            self.save_version_data()
            
            print(f"✅ Versão incrementada: {current} -> {new_version}")
            
        except Exception as e:
            print(f"❌ Erro ao incrementar versão: {str(e)}")
            raise

if __name__ == "__main__":
    # Para facilitar o uso direto pelo Makefile
    analyzer = VersionAnalyzer()
    analyzer.smart_bump() 