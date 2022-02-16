from .entity_error import EntityErrors


class DatasetFileLocationError(EntityErrors):

    def get_errors_to_str(self):
        err_lst = []
        for er in self.get_errors():  # EntityErrors.get_errors
            # print ('er.error_desc = {}'.format(er.error_desc))
            err_lst.append({'error_desc': er.error_desc, 'error_number': er.error_number})

        error = {
            'file': str(self.entity.location_path),
            'errors': err_lst  # EntityErrors.get_errors(self)
        }
        return error
