def is_in_label(adr, drug_label="diarrhia,headache,nausea") -> bool:
    list_of_adr_in_label = drug_label.split(",")
    adr_is_in_label = [e for e in list_of_adr_in_label if e==adr]

    return adr_is_in_label
