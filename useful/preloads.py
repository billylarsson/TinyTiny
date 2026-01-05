
def preloads(hack_string: str = ''):
    import sys, os

    args: list[str] = sys.argv[1:]
    if not args and not os.path.exists('/home/plutonergy/'):
        return

    def operation(demand: str) -> bool:
        return demand in [x.lower().lstrip('-_') for x in (args or hack_string.split())]

    post_exit: bool = False
    if operation('update_database'):
        from useful.update_database import make_quick_db
        make_quick_db()
        post_exit = True

    if operation('import_owned'):
        from useful.database import Owned
        Owned().update_ownedfile_from_plmtg()
        post_exit = True

    if operation('update_legals'):
        from useful.update_database import make_quick_legal_db
        make_quick_legal_db()
        post_exit = True

    if operation('zip_source'):
        import os, zipfile, time
        from useful.update_database import price_datas,legal_card_datas,db_path_card_datas,fresh_databases
        zip_loc: str = '/home/plutonergy/tmp/tinytiny.zip'

        print(f'starting to source-copy... ')
        timer_start: float = time.time()
        base_folder: str = os.sep.join(__file__.split(os.sep)[:-2])

        dummy_file: str = f'{base_folder}{os.sep}.dummy'
        dummy = open(dummy_file, 'w')
        dummy.close()

        paths: set | list = set()
        skip: set = {'scryfall_ids.csv', 'user_datas.sqlite'}
        side_store: set = {price_datas, legal_card_datas, db_path_card_datas}

        with zipfile.ZipFile(fresh_databases, mode='w') as zf:
            for path in side_store:
                arcname: str = path[len(base_folder):]
                print(f'\33[38:5:249mrefreshed\33[0m ..{arcname}')
                zf.write(path, arcname=arcname, compress_type=zipfile.ZIP_DEFLATED)

        unwanted_path = lambda p: p in skip or any(d.startswith(pre) for pre in ['.', '__'] for d in p.split(os.sep))

        for (folder, subs, files) in os.walk(base_folder):
            if unwanted_path(folder):
                continue

            for f in files:
                path = f'{folder}{os.sep}{f}'
                if unwanted_path(f):
                    continue
                else:
                    paths.add(path)


        with zipfile.ZipFile(zip_loc, mode='w') as zf:
            paths = list(paths)
            paths.sort()
            paths.sort(key=lambda x: x.count(os.sep), reverse=True)
            for path in paths:
                arcname: str = path[len(base_folder):]
                if path in side_store:
                    path = dummy_file

                print(f'\33[38:5:249madding\33[0m ..{arcname}')
                zf.write(path, arcname=arcname, compress_type=zipfile.ZIP_DEFLATED)

        os.remove(dummy_file)

        timer_end: float = time.time() - timer_start
        print(f'source-zipped in {round(timer_end, 2)} seconds into {zip_loc} {os.path.getsize(zip_loc) // 1_000} kb')
        post_exit = True

    if operation('import_prices'):
        from useful.update_database import make_prices_db
        make_prices_db()
        post_exit = True


    if post_exit:
        sys.exit()