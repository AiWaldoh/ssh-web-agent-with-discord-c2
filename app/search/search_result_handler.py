class SearchResultHandler:
    def format_search_result(self, search_result):
        result_message = ""
        for item in search_result:
            description = f"```{item.description}```"
            result_message += f" <{item.url}>\n{description}\n"
        return result_message
