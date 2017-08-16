from sqlalchemy import Column
from sqlalchemy.types import String, Date
from sqlalchemy.dialects.postgresql import ARRAY, DATERANGE
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RouteCode(Base):
    __tablename__ = 'route_code'

    route_code = Column(String(5), primary_key=True)
    date_range = Column(DATERANGE, primary_key=True)
    quote_date = Column(Date)
    description = Column(String(16))
    atb_desc = Column(String(140))

    # These inclusions/exclusions are from RJFA/RTE
    # and are associated with the date range above.
    # There is no concept of an 'any/either' inclusion
    crs_inclusions = Column(ARRAY(String(3)))
    crs_exclusions = Column(ARRAY(String(3)))

    # Following from RJRG/RGK:
    rgk_crs_inclusions = Column(ARRAY(String(3)))
    rgk_crs_anys = Column(ARRAY(String(3)))  # supercedes crs_inclusions
    rgk_crs_exclusions = Column(ARRAY(String(3)))

    london_marker = Column(String(1))
    # RJRG/RGK also is the only source for TOC/Mode exclusions:
    toc_inclusions = Column(ARRAY(String(2)))
    toc_exclusions = Column(ARRAY(String(2)))
    mode_inclusions = Column(ARRAY(String(3)))
    mode_exclusions = Column(ARRAY(String(3)))

    def __repr__(self):
        return '<ROUTE_CODE %s: %s>' % (self.route_code, self.description)


if __name__ == '__main__':
    from lib.config import get_dburi
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    engine = create_engine(get_dburi())
    session = sessionmaker(bind=engine)()
    route_codes = session.query(RouteCode).all()
    # (duplicates have different date validities)
    import pdb
    pdb.set_trace()
    pass  # have a look at the route_codes in the Python debugger
