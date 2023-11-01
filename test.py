from lal_modules import core
senders = ["test1 "]
senders_addr = ["test3333"]
receivers = [""]


receivers = [""]
receivers_addr = [""]
ccs = [""]
cc_addr = [""]
text = "qeqwnejkqnjk wenkjqwnekqnwkj enklfnklsandjkanjkn jkasdnjfksd"

output_filename = "test.pdf"

core.generate_text_and_letter(senders, senders_addr,
                                receivers, receivers_addr,
                                ccs, cc_addr,
                                text)
core.merge_text_and_letter(output_filename)
core.clean_temp_files()

print('Done. Filename: ', output_filename)