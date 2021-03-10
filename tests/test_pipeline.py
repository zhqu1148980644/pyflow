from pyflow import *


# @task
# def fq2fa(fq: File):
#     """
#     fq2fa {fq} > {set_output}
#     """
#     prefix = str(fq).rstrip(".fq")
#
#     return "{prefix}.fa"
#
#
# @task
# def blast(fa: File, db: File):
#     """
#     blastn -db {db} -in {fa} -out {set_output}
#     """
#     prefix = str(fa).rstrip('.fa')
#
#     return "{prefix}.txt"
#
#
# @task
# def count_lines(fa: File) -> int:
#     with open(fa) as f:
#         return len(f.readlines())
#
#
# @flow
# def test_flow(fa: File, db: File) -> ""
#     fq2fa(fq)
#     blast_results = blast(fa, db)  # both is ok
#     blast_results = blast(fq2fa.out, db)