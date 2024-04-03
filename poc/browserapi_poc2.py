# this is equivalent to the discord client I think
# class WebNavigatorFacade:
#     def __init__(self, browser: PlaywrightBrowserWrapper):
#         self.browser = browser
#         self.page_analyzer = PageAnalyzer(browser)
#         self.page_info_saver = PageInfoSaver()
#         self.feedback_provider = FeedbackProvider(
#             self.page_analyzer, self.page_info_saver
#         )
#         self.interaction_handler = InteractionHandler(browser, self.feedback_provider)

#     def process_command(self, command: str, params: Dict[str, str]) -> str:
#         try:
#             feedback = self.interaction_handler.handle_command(command, params)
#             return feedback
#         except Exception as e:
#             return self.feedback_provider.get_error_feedback(str(e))


# class InteractionHandler:
#     def __init__(self, browser: PlaywrightBrowserWrapper, feedback_provider):
#         self.browser = browser
#         self.feedback_provider = feedback_provider
#         self._register_commands()

#     def _register_commands(self):
#         AITaskRegistry.register("take_screenshot", TakeScreenshotTask(self.browser))
#         AITaskRegistry.register(
#             "goto", GoToPageTask(self.browser, self.feedback_provider)
#         )
#         AITaskRegistry.register("click", ClickElementTask(self.browser))
#         AITaskRegistry.register("fill", FillInputTask(self.browser))
#         AITaskRegistry.register(
#             "form_details", FormDetailsTask(self.browser, self.feedback_provider)
#         )
#         AITaskRegistry.register(
#             "links", LinksTask(self.browser, self.feedback_provider)
#         )
#         AITaskRegistry.register(
#             "buttons", ButtonsTask(self.browser, self.feedback_provider)
#         )
#         AITaskRegistry.register("submit", SubmitFormTask(self.browser))
#         AITaskRegistry.register("page_source", GetPageSourceTask(self.browser))
#         AITaskRegistry.register("current_url", GetCurrentUrlTask(self.browser))

#     def handle_command(self, command: str, params: Dict[str, str]) -> str:
#         task_command = AITaskRegistry.get_command(command)

#         if task_command:
#             try:
#                 feedback = task_command.execute(params)
#                 return feedback
#             except Exception as e:
#                 return self.feedback_provider.get_error_feedback(str(e))
#         else:
#             return self.feedback_provider.get_error_feedback(
#                 f"Unknown command: {command}"
#             )


# def test_poc2():
#     # Create an instance of the PlaywrightBrowserWrapper
#     browser = PlaywrightBrowserWrapper(browser_type="chromium", headless=False)

#     # Create an instance of the WebNavigatorFacade
#     web_navigator = WebNavigatorFacade(browser)

#     # Test case 1: Navigate to a website
#     command = "goto"
#     params = {"url": "https://blog.cloudflare.com/workers-ai"}
#     feedback = web_navigator.process_command(command, params)
#     print(feedback)

#     # # Test case 3: Fill an input field
#     command = "fill"
#     params = {"selector": ".top-subscribe-form-input", "value": "k123k@duck.com"}
#     feedback = web_navigator.process_command(command, params)
#     print(feedback)

#     # # Test case 2: Click on an element
#     command = "click"
#     params = {"selector": "button.top-subscribe-form-button"}
#     feedback = web_navigator.process_command(command, params)
#     print(feedback)

#     # take screenshot
#     command = "take_screenshot"
#     params = {"file_path": "screenshot.png"}
#     feedback = web_navigator.process_command(command, params)
#     print(feedback)

#     # # Test case 4: Get form details
#     # command = "form_details"
#     # params = {}
#     # feedback = web_navigator.process_command(command, params)
#     # print(feedback)

#     # # Test case 5: Get links on the page
#     # command = "links"
#     # params = {}
#     # feedback = web_navigator.process_command(command, params)
#     # print(feedback)

#     # # Test case 6: Get buttons on the page
#     # command = "buttons"
#     # params = {}
#     # feedback = web_navigator.process_command(command, params)
#     # print(feedback)

#     # # Test case 7: Unknown command
#     # command = "unknown"
#     # params = {}
#     # feedback = web_navigator.process_command(command, params)
#     # print(feedback)

#     # Close the browser
#     browser.close()


if __name__ == "__main__":

    testing_poc_2 = True
    # if testing_poc_2:
    #     test_poc2()
