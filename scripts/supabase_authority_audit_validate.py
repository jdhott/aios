from pathlib import Path

def main():
    r=Path(__file__).resolve().parents[1]
    runtime=(r/'run_aios.py').read_text()
    audit=(r/'core/storage/supabase_authority_audit.py').read_text()
    checks={
      'Supabase-only bootstrap':
          'if AIOS_DATASTORE == "supabase":' in runtime
          and 'install_supabase_authority_audit' in runtime,
      'Observes POST/PATCH/DELETE':
          all(x in audit for x in ["_record('POST'","_record('PATCH'","_record('DELETE'"]),
      'Allows block UI':
          'allowed_interface' in audit and '/v1/blocks/' in audit,
      'Allows task mirrors':
          'allowed_task_mirror' in audit,
      'Flags project creation':
          'Project database page creation in Supabase mode' in audit,
      'Flags page mutation':
          'unexpected_authoritative' in audit and '/v1/pages/' in audit,
      'Database query POSTs excluded as reads':
          "/v1/databases/[^/?#]+/query" in audit,
      'Clean graduation result':
          'SUPABASE CORE PERSISTENCE AUTHORITY CLEAN' in audit,
    }
    for k,v in checks.items():
        print(('PASS' if v else 'FAIL')+': '+k)
    if not all(checks.values()):
        raise SystemExit(1)
    print('\nRESULT: SUPABASE AUTHORITY AUDIT STRUCTURE VALID')

if __name__=='__main__':
    main()
