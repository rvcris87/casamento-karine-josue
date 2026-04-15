#!/usr/bin/env python3
"""
Script de teste para validar a conexão com o banco de dados PostgreSQL.
Execute com: python test_connection.py
"""

import sys
from db import get_connection, get_presentes

def test_database_connection():
    """Testa a conexão com o banco de dados."""
    print("🔍 Testando conexão com o banco de dados...")
    print("-" * 50)
    
    try:
        connection = get_connection()
        print("✅ Conexão estabelecida com sucesso!")
        
        # Testar cursor
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print(f"✅ Versão do PostgreSQL: {db_version[0]}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {str(e)}")
        print("\n💡 Dicas:")
        print("   1. Verifique se o arquivo .env existe")
        print("   2. Confirme se DATABASE_URL está preenchida corretamente")
        print("   3. Verifique sua conexão de rede e firewall")
        return False


def test_presentes_query():
    """Testa se consegue buscar presentes do banco."""
    print("\n🔍 Testando busca de presentes...")
    print("-" * 50)
    
    try:
        presentes = get_presentes()
        
        if presentes:
            print(f"✅ {len(presentes)} presente(s) encontrado(s)!")
            for presente in presentes:
                print(f"   • {presente.get('titulo', 'N/A')} - {presente.get('valor', 'N/A')}")
        else:
            print("⚠️  Nenhum presente encontrado no banco.")
            print("   Dica: Execute o script SETUP_DATABASE.sql para inserir presentes.")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao buscar presentes: {str(e)}")
        return False


def main():
    """Executa todos os testes."""
    print("\n")
    print("=" * 50)
    print("🧪 TESTE DE CONEXÃO - CASAMENTO KARINE & JOSUÉ")
    print("=" * 50)
    print("\n")
    
    # Teste 1: Conexão
    connection_ok = test_database_connection()
    
    # Teste 2: Query de presentes
    presentes_ok = test_presentes_query() if connection_ok else False
    
    # Resumo
    print("\n")
    print("=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)
    print(f"Conexão com banco: {'✅ OK' if connection_ok else '❌ ERRO'}")
    print(f"Query de presentes: {'✅ OK' if presentes_ok else '⚠️  AVISO'}")
    print("=" * 50)
    print("\n")
    
    if connection_ok:
        print("🎉 Tudo pronto para usar! Execute: flask run")
        return 0
    else:
        print("❌ Corrija os erros acima antes de continuar.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
