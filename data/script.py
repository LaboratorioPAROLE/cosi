import csv

KIParla_folder = "/Users/ludovica/Documents/KIParla/KIParla-collection/tsv"

with open("dunque.csv", encoding="utf-8-sig") as fin, \
    open("dunque_processed.csv", "w") as fout:
	file = csv.DictReader(fin, delimiter=";",restval="_")
	fieldnames = (file.fieldnames or []) + ["token_id"]
	writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=";", restval="_")
	writer.writeheader()
	for line in file:
		conv = line["Reference"]
		left_ctx = ''.join(line["Left"].split("//")).split()
		kwic = line["KWIC"]
		right_ctx = ''.join(line["Right"].split("//")).split()

		kiparla_file = f"{KIParla_folder}/{conv}.vert.tsv"

		with open(kiparla_file) as fin_kiparla:
			kiparla_csv = csv.DictReader(fin_kiparla, delimiter="\t",restval="_")

			elements = [(x["token_id"], x["form"]) for x in kiparla_csv if x["type"] == "linguistic"]

			possibilities = {}
			for i, (id, element) in enumerate(elements):
				if element == kwic:
					left_poss = elements[max(0, i-len(left_ctx)):i]
					right_poss = elements[i+1:min(len(elements), i+len(right_ctx))]
					left_score = 0
					for left_id, left_element in left_poss:
						if left_element in left_ctx:
							left_score +=1
					right_score = 0
					for left_id, right_element in right_poss:
						if right_element in right_ctx:
							right_score +=1
					possibilities[id] = left_score + right_score
			sorted_possibilities = list(sorted(possibilities.items(), key=lambda x: -x[1]))

			line["token_id"] = sorted_possibilities[0][0]
			writer.writerow(line)
			# print(line)
			# print(sorted_possibilities[0])
			# input()