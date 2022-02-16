from .entity_error import EntityErrors


class FileError(EntityErrors):

    def row_errors_count(self):
        row_err_cnt = 0
        # verify that rows object exists (it can be a case that rows were not instantiated yet due to
        # earlier errors with file processing
        if self.entity.rows:
            for d in self.entity.rows.values():
                if d.error.exist():
                    row_err_cnt += 1
        return row_err_cnt

    def get_errors_to_str(self):
        err_lst = []
        for er in EntityErrors.get_errors(self):
            # print ('er.error_desc = {}'.format(er.error_desc))
            err_lst.append({'error_desc': er.error_desc, 'error_number': er.error_number})

        error = {
            'file': str(self.entity.filepath),
            'header': self.entity.headers,
            'errors': err_lst
        }
        return error
